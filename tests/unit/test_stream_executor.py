# ruff: noqa: PLR6301, PLR2004 - testes em classe e literais nos asserts, como no
# resto da suíte.
import asyncio
import dataclasses
import logging
import re

import pytest

from chatgraph.stream.connection import _Connection  # noqa: PLC2701
from chatgraph.stream.errors import (
    CommandFailedError,
    CommandTimeoutError,
    ConnectionLostError,
    FrameTooLargeError,
    InvalidDeliveryError,
    SessionNotOwnedError,
    StreamClosedError,
    StreamError,
    is_session_not_owned,
)
from tests.unit.stream_fake_router import (
    ConnScript,
    eventually,
    stream_client,
)

CHAT = {'user_id': 'user-1', 'company_id': 'company-1'}
OTHER_CHAT = {'user_id': 'user-2', 'company_id': 'company-1'}
NOT_OWNED = 'session_not_owned: session is on menu geral'


def commands(conn) -> list[dict]:
    return conn.of_type('command')


def all_commands(router) -> list[dict]:
    return [f for conn in router.conns for f in commands(conn)]


def fast(settings, **changes):
    return dataclasses.replace(settings, **changes)


@pytest.mark.unit
class TestCommandResult:
    @pytest.mark.asyncio
    async def test_ok_returns_and_sends_one_well_formed_frame(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            await client.command('set_route', CHAT, {'route': 'a'}, True)

        frame = commands(fake_router.conns[0])[0]
        assert re.fullmatch(r'[0-9a-f]{16}-1', frame['cmd_id'])
        assert frame == {
            'type': 'command',
            'cmd_id': frame['cmd_id'],
            'name': 'set_route',
            'chat_id': CHAT,
            'payload': {'route': 'a'},
        }

    @pytest.mark.asyncio
    async def test_cmd_ids_are_sequential_within_one_client(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            await client.command('send', CHAT, {}, False)
            await client.command('send', CHAT, {}, False)

        ids = [f['cmd_id'] for f in commands(fake_router.conns[0])]
        assert [i.split('-')[1] for i in ids] == ['1', '2']
        assert ids[0].split('-')[0] == ids[1].split('-')[0]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('script', 'expected'),
        [
            (
                ConnScript(command_error='boom'),
                (CommandFailedError, 'send: boom'),
            ),
            (
                ConnScript(command_omit_ok=True),
                (CommandFailedError, 'send: '),
            ),
            (
                ConnScript(command_error=NOT_OWNED),
                (SessionNotOwnedError, NOT_OWNED),
            ),
        ],
        ids=['error', 'ok_missing', 'session_not_owned'],
    )
    async def test_failed_result_maps_to_typed_error_without_resend(
        self, fake_router, stream_settings, script, expected
    ):
        error_type, message = expected
        fake_router.default = script
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            with pytest.raises(error_type) as exc_info:
                await client.command('send', CHAT, {}, True)

            await asyncio.sleep(0.05)

        assert str(exc_info.value) == message
        assert len(all_commands(fake_router)) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'case',
        [
            (
                ConnScript(command_error='boom'),
                'Stream command failed',
                logging.ERROR,
            ),
            (
                ConnScript(command_error=NOT_OWNED),
                'Stream command session not owned',
                logging.WARNING,
            ),
        ],
        ids=['failed_is_error', 'not_owned_is_warning'],
    )
    async def test_failure_log_level(
        self, fake_router, stream_settings, caplog, case
    ):
        script, text, level = case
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        fake_router.default = script
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            with pytest.raises(StreamError):
                await client.command('send', CHAT, {}, False)

        matching = [r for r in caplog.records if text in r.getMessage()]
        assert [r.levelno for r in matching] == [level]
        assert 'name=send' in matching[0].getMessage()
        assert 'cmd_id=' in matching[0].getMessage()

    @pytest.mark.asyncio
    async def test_session_not_owned_is_visible_through_is_session_not_owned(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(command_error=NOT_OWNED)
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            with pytest.raises(SessionNotOwnedError) as exc_info:
                await client.command('send', CHAT, {}, False)

        assert is_session_not_owned(exc_info.value)


@pytest.mark.unit
class TestCommandTimeout:
    @pytest.mark.asyncio
    async def test_silent_router_times_out_and_late_result_is_harmless(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        fake_router.default = ConnScript(command_silent=True)
        settings = fast(stream_settings, command_timeout=0.1)
        async with stream_client(fake_router, settings) as (client, _):
            await client.connect()
            conn = fake_router.conns[0]
            started = asyncio.get_running_loop().time()

            with pytest.raises(CommandTimeoutError):
                await client.command('send', CHAT, {}, False)
            elapsed = asyncio.get_running_loop().time() - started

            cmd_id = commands(conn)[0]['cmd_id']
            await conn.send({
                'type': 'command_result',
                'cmd_id': cmd_id,
                'ok': True,
            })
            await eventually(
                lambda: any(
                    'Stream late command_result' in r.getMessage()
                    for r in caplog.records
                )
            )

        assert 0.09 <= elapsed < 0.4
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


@pytest.mark.unit
class TestPendingCleanup:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('script', 'error_type'),
        [
            (ConnScript(), None),
            (ConnScript(command_silent=True), CommandTimeoutError),
            (ConnScript(command_abort=True), ConnectionLostError),
        ],
        ids=['result', 'timeout', 'drop'],
    )
    async def test_pending_is_removed_and_connection_goes_idle(
        self, fake_router, stream_settings, script, error_type
    ):
        fake_router.default = script
        settings = fast(stream_settings, command_timeout=0.1)
        async with stream_client(fake_router, settings) as (client, _):
            await client.connect()
            conn = client._current

            if error_type is None:
                await client.command('send', CHAT, {}, False)
            else:
                with pytest.raises(error_type):
                    await client.command('send', CHAT, {}, False)

            assert conn.pending_count() == 0
            assert conn._idle.is_set()
            assert client.pending_commands() == 0

    @pytest.mark.asyncio
    async def test_pending_is_registered_while_the_command_is_in_flight(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(command_delay=0.2)
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            conn = client._current

            task = asyncio.create_task(client.command('send', CHAT, {}, False))
            await eventually(lambda: conn.pending_count() == 1)
            assert not conn._idle.is_set()
            assert client.pending_commands() == 1

            await task
            assert client.pending_commands() == 0


@pytest.mark.unit
class TestChatOrdering:
    @pytest.mark.asyncio
    async def test_same_chat_serializes_commands(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(command_delay=0.2)
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            conn = fake_router.conns[0]

            first = asyncio.create_task(
                client.command('send', CHAT, {}, False)
            )
            await eventually(lambda: len(commands(conn)) == 1)
            second = asyncio.create_task(
                client.command('send', CHAT, {}, False)
            )
            await asyncio.gather(first, second)

            assert client._chat_locks == {}

        arrivals = [t for t, f in conn.frames if f.get('type') == 'command']
        first_result_at = conn.results()[0][0]
        assert arrivals[1] >= first_result_at

    @pytest.mark.asyncio
    async def test_different_chats_run_in_parallel(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(command_delay=0.2)
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            conn = fake_router.conns[0]

            first = asyncio.create_task(
                client.command('send', CHAT, {}, False)
            )
            await eventually(lambda: len(commands(conn)) == 1)
            second = asyncio.create_task(
                client.command('send', OTHER_CHAT, {}, False)
            )
            await asyncio.gather(first, second)

        arrivals = [t for t, f in conn.frames if f.get('type') == 'command']
        first_result_at = conn.results()[0][0]
        assert arrivals[1] < first_result_at


@pytest.mark.unit
class TestConnectionWait:
    @pytest.mark.asyncio
    async def test_command_waits_for_the_next_connection(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            fake_router.default = ConnScript(status=503)
            fake_router.conns[0].abort()
            await eventually(lambda: client._current is None)

            task = asyncio.create_task(client.command('send', CHAT, {}, False))
            await asyncio.sleep(0.15)
            assert not task.done()
            fake_router.default = ConnScript()
            await task

        assert commands(fake_router.conns[0]) == []
        assert len(commands(fake_router.conns[-1])) == 1

    @pytest.mark.asyncio
    async def test_command_times_out_when_router_keeps_refusing(
        self, fake_router, stream_settings
    ):
        settings = fast(stream_settings, command_timeout=0.1)
        async with stream_client(fake_router, settings) as (client, _):
            await client.connect()
            fake_router.default = ConnScript(status=503)
            fake_router.conns[0].abort()
            await eventually(lambda: client._current is None)

            with pytest.raises(
                CommandTimeoutError, match='send aguardando conexão'
            ):
                await client.command('send', CHAT, {}, False)

    @pytest.mark.asyncio
    async def test_dead_current_waits_for_ready_event_without_spinning(
        self, fake_router, stream_settings, monkeypatch, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            monkeypatch.setattr(client, '_demote', lambda conn: None)
            fake_router.default = ConnScript(status=503)
            fake_router.conns[0].abort()
            dead = client._current
            await eventually(dead.closed.is_set)

            task = asyncio.create_task(client.command('send', CHAT, {}, False))
            await asyncio.sleep(0.15)
            fake_router.default = ConnScript()
            await task

        laps = [
            r
            for r in caplog.records
            if 'Stream command waiting for connection' in r.getMessage()
        ]
        assert 1 <= len(laps) <= 2

    @pytest.mark.asyncio
    async def test_close_wakes_a_command_waiting_for_connection(
        self, fake_router, stream_settings
    ):
        settings = fast(stream_settings, command_timeout=5.0)
        async with stream_client(fake_router, settings) as (client, _):
            await client.connect()
            fake_router.default = ConnScript(status=503)
            fake_router.conns[0].abort()
            await eventually(lambda: client._current is None)

            task = asyncio.create_task(client.command('send', CHAT, {}, False))
            await asyncio.sleep(0.05)
            await client.close()

            with pytest.raises(StreamClosedError):
                await asyncio.wait_for(task, 1.0)


@pytest.mark.unit
class TestDropWithPending:
    @pytest.mark.asyncio
    async def test_idempotent_command_is_resent_on_the_new_connection(
        self, fake_router, stream_settings
    ):
        fake_router.scripts = [ConnScript(command_abort=True)]
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            await client.command('set_route', CHAT, {'route': 'a'}, True)

        first = commands(fake_router.conns[0])
        second = commands(fake_router.conns[1])
        assert len(first) == 1
        assert len(second) == 1
        assert first[0]['payload'] == second[0]['payload'] == {'route': 'a'}

    @pytest.mark.asyncio
    async def test_non_idempotent_command_fails_with_connection_lost(
        self, fake_router, stream_settings
    ):
        fake_router.scripts = [ConnScript(command_abort=True)]
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            with pytest.raises(ConnectionLostError):
                await client.command('send', CHAT, {}, False)

            await asyncio.sleep(0.1)

        assert len(all_commands(fake_router)) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('name', 'idempotent'), [('send', False), ('set_route', True)]
    )
    async def test_result_followed_by_drop_is_success(
        self, fake_router, stream_settings, monkeypatch, name, idempotent
    ):
        real_resolve = _Connection.resolve

        def resolve_then_drop(conn, frame):
            real_resolve(conn, frame)
            conn._die('dropped right after the result')

        monkeypatch.setattr(_Connection, 'resolve', resolve_then_drop)
        fake_router.scripts = [ConnScript(command_abort_after_reply=True)]
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            await client.command(name, CHAT, {}, idempotent)

            await asyncio.sleep(0.1)

        assert len(all_commands(fake_router)) == 1


@pytest.mark.unit
class TestFrameLimits:
    @pytest.mark.asyncio
    async def test_frame_above_1_mib_is_rejected_without_writing(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            payload = {'message': {'text': 'x' * (2 * 1024 * 1024)}}

            with pytest.raises(FrameTooLargeError, match='send'):
                await client.command('send', CHAT, payload, False)

            await asyncio.sleep(0.05)

        assert all_commands(fake_router) == []
        assert client.pending_commands() == 0


@pytest.mark.unit
class TestClosedClient:
    @pytest.mark.asyncio
    async def test_command_after_close_raises_closed(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            await client.close()

            with pytest.raises(StreamClosedError):
                await client.command('send', CHAT, {}, False)


@pytest.mark.unit
class TestIsSessionNotOwned:
    def test_direct_instance(self):
        assert is_session_not_owned(SessionNotOwnedError('x'))

    def test_wrapped_through_cause(self):
        wrapper = ValueError('wrap')
        wrapper.__cause__ = SessionNotOwnedError('x')

        assert is_session_not_owned(wrapper)

    def test_wrapped_through_context(self):
        wrapper = Exception('Erro ao enviar mensagem')
        wrapper.__context__ = SessionNotOwnedError('x')

        assert is_session_not_owned(wrapper)

    def test_unrelated_exception_is_false(self):
        assert not is_session_not_owned(ValueError('x'))
        assert not is_session_not_owned(CommandFailedError('send: boom'))

    def test_cycle_terminates_with_false(self):
        first = ValueError('a')
        second = ValueError('b')
        first.__context__ = second
        second.__context__ = first

        assert not is_session_not_owned(first)

    @pytest.mark.parametrize(('levels', 'expected'), [(9, True), (10, False)])
    def test_chain_is_followed_for_at_most_10_levels(self, levels, expected):
        exc: BaseException = SessionNotOwnedError('x')
        for _ in range(levels):
            wrapper = ValueError('wrap')
            wrapper.__cause__ = exc
            exc = wrapper

        assert is_session_not_owned(exc) is expected


@pytest.mark.unit
class TestInvalidDeliveryError:
    @pytest.mark.parametrize(
        'reason', ['invalid_payload', 'invalid_observation']
    )
    def test_carries_reason(self, reason):
        error = InvalidDeliveryError(reason)

        assert error.reason == reason
        assert str(error) == reason
        assert isinstance(error, StreamError)
