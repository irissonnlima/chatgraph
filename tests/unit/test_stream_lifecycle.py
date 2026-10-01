# ruff: noqa: PLR2004, PLR6301 - testes em classe e literais nos asserts, como no
# resto da suíte.
import asyncio
import dataclasses
import logging

import pytest

from chatgraph.stream.client import DRAIN_SENTINEL
from chatgraph.stream.connection import _Connection  # noqa: PLC2701
from chatgraph.stream.errors import StreamClosedError
from tests.unit.stream_fake_router import (
    ConnScript,
    eventually,
    make_deliver,
    stream_client,
)


def stream_tasks() -> list[asyncio.Task]:
    return [
        t
        for t in asyncio.all_tasks()
        if t.get_name().startswith('chatgraph-stream-') and not t.done()
    ]


@pytest.mark.unit
class TestKeepalive:
    @pytest.mark.asyncio
    async def test_ping_frames_are_sent_every_heartbeat(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(heartbeat_s=1)
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            conn = fake_router.conns[0]

            await eventually(lambda: conn.of_type('ping'), timeout=0.3)

    @pytest.mark.asyncio
    async def test_silent_router_is_declared_dead_and_redialed(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        fake_router.scripts = [ConnScript(heartbeat_s=1, silent=True)]
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            await eventually(lambda: len(fake_router.conns) == 2, timeout=1.0)

        assert any(
            'no frame within 3x heartbeat_s' in r.getMessage()
            for r in caplog.records
        )


@pytest.mark.unit
class TestReconnect:
    @pytest.mark.asyncio
    async def test_redial_backs_off_with_growing_delays(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(abort_after_welcome=True)
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            await eventually(lambda: len(fake_router.attempts) >= 4)

        instants = [a.at for a in fake_router.attempts[:4]]
        intervals = [b - a for a, b in zip(instants, instants[1:])]
        for interval, expected in zip(intervals, (0.01, 0.02, 0.04)):
            assert interval >= expected - 0.005

    @pytest.mark.asyncio
    async def test_redial_after_drop_delivers_on_new_connection(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            fake_router.conns[0].abort()

            await eventually(lambda: len(fake_router.conns) == 2)
            second = fake_router.conns[1]
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-1'
                )
            )
            await second.send(make_deliver('d1', 'm1'))
            await eventually(lambda: sink.items)

        assert sink.items[0]['msg_id'] == 'm1'

    @pytest.mark.asyncio
    async def test_counter_resets_after_stable_connection(
        self, fake_router, stream_settings
    ):
        dropping = ConnScript(abort_after_welcome=True)
        fake_router.scripts = [dropping, dropping, dropping, ConnScript()]
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            await eventually(lambda: len(fake_router.conns) == 4)
            stable = fake_router.conns[3]
            await asyncio.sleep(0.35)

            aborted_at = asyncio.get_running_loop().time()
            stable.abort()
            await eventually(lambda: len(fake_router.attempts) >= 5)

        delay = fake_router.attempts[4].at - aborted_at
        assert delay < 0.01 + 0.05

    @pytest.mark.asyncio
    async def test_unexpected_error_in_read_loop_redials_before_death_check(
        self, fake_router, stream_settings, monkeypatch, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        real_dispatch = _Connection._dispatch
        raised = []

        async def failing_dispatch(self, frame):
            if frame.get('type') == 'deliver' and not raised:
                raised.append(True)
                raise RuntimeError('boom')
            await real_dispatch(self, frame)

        monkeypatch.setattr(_Connection, '_dispatch', failing_dispatch)
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            first = fake_router.conns[0]

            await first.send(make_deliver('d1', 'm1'))
            await eventually(lambda: len(fake_router.conns) == 2, timeout=0.4)

        messages = [r.getMessage() for r in caplog.records]
        assert any('read loop failed: RuntimeError' in m for m in messages)
        assert any('Stream task crashed' in m for m in messages)


@pytest.mark.unit
class TestGoAway:
    @pytest.mark.asyncio
    async def test_no_loss_while_replacement_is_not_ready(
        self, fake_router, stream_settings
    ):
        fake_router.scripts = [ConnScript(), ConnScript(welcome_delay=0.3)]
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            first = fake_router.conns[0]

            await first.send({'type': 'goaway', 'reason': 'shutdown'})
            await eventually(lambda: len(fake_router.conns) == 2)
            second = fake_router.conns[1]
            await first.send(make_deliver('d1', 'm1'))
            await eventually(lambda: first.of_type('ack'))
            still_open = not first.closed.is_set()

            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-1'
                )
            )
            await eventually(first.closed.is_set)
            await second.send(make_deliver('d2', 'm2'))
            await eventually(lambda: len(sink.items) == 2)

        assert still_open
        assert first.close_code == 1000
        assert first.close_reason == 'goaway: replaced'
        assert first.closed_at >= second.welcome_at
        assert [i['msg_id'] for i in sink.items] == ['m1', 'm2']

    @pytest.mark.asyncio
    async def test_replacement_refused_with_503_retries_without_error(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger='chatgraph.system')
        fake_router.scripts = [
            ConnScript(),
            ConnScript(status=503, body='{"error":"draining"}'),
        ]
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

            await fake_router.conns[0].send({
                'type': 'goaway',
                'reason': 'shutdown',
            })
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-2'
                )
            )

        messages = [r.getMessage() for r in caplog.records]
        assert any('Stream goaway received' in m for m in messages)
        assert any('Stream connection replaced' in m for m in messages)
        assert any('class=short' in m for m in messages)
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]

    @pytest.mark.asyncio
    async def test_current_is_demoted_when_old_dies_before_the_swap(
        self, fake_router, stream_settings
    ):
        fake_router.scripts = [ConnScript()]
        fake_router.default = ConnScript(status=503)
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            first = fake_router.conns[0]
            old = client._current

            await first.send({'type': 'goaway', 'reason': 'shutdown'})
            await eventually(lambda: len(fake_router.attempts) >= 3)
            first.abort()
            await eventually(lambda: client._current is None)
            window_end = asyncio.get_running_loop().time() + 0.3
            while asyncio.get_running_loop().time() < window_end:
                assert client._current is None
                await asyncio.sleep(0.01)

            fake_router.default = ConnScript()
            await eventually(lambda: client._current is not None)

            assert client._current is not old
            assert client._current.id.startswith('conn-')

    @pytest.mark.asyncio
    async def test_in_flight_command_finishes_on_old_connection_then_it_closes(
        self, fake_router, stream_settings
    ):
        settings = dataclasses.replace(stream_settings, command_timeout=2.0)
        chat = {'user_id': 'user-1', 'company_id': 'company-1'}
        fake_router.scripts = [ConnScript(command_delay=0.4)]
        async with stream_client(fake_router, settings) as (client, _):
            await client.connect()
            first = fake_router.conns[0]
            in_flight = asyncio.create_task(
                client.command('set_route', chat, {'route': 'a'}, True)
            )
            await eventually(lambda: first.of_type('command'))

            await first.send({'type': 'goaway', 'reason': 'shutdown'})
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-1'
                )
            )
            assert not in_flight.done()
            assert not first.closed.is_set()

            await in_flight
            await eventually(first.closed.is_set, timeout=1.0)
            await client.command('send', chat, {}, False)

        second = fake_router.conns[1]
        assert first.closed_at - first.results()[0][0] <= 0.2
        assert first.close_code == 1000
        assert [f['name'] for f in first.of_type('command')] == ['set_route']
        assert [f['name'] for f in second.of_type('command')] == ['send']


@pytest.mark.unit
class TestDrain:
    @pytest.mark.asyncio
    async def test_drain_nacks_new_deliveries_and_sentinel_comes_last(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (
            client,
            sink,
        ):
            await client.connect()
            conn = fake_router.conns[0]
            await conn.send(make_deliver('d1', 'm1'))
            await eventually(lambda: conn.of_type('ack'))

            await client.begin_drain()
            await client.begin_drain()
            await conn.send(make_deliver('d2', 'm2'))
            await eventually(lambda: conn.of_type('nack'))

        assert conn.of_type('nack') == [
            {
                'type': 'nack',
                'delivery_id': 'd2',
                'msg_id': 'm2',
                'retryable': True,
                'error': 'draining',
            }
        ]
        assert len(sink.items) == 2
        assert sink.items[0]['msg_id'] == 'm1'
        assert sink.items[-1] is DRAIN_SENTINEL


@pytest.mark.unit
class TestClose:
    @pytest.mark.asyncio
    async def test_close_is_idempotent_and_leaves_no_task(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            first = fake_router.conns[0]

            await client.close()
            await client.close()

            with pytest.raises(StreamClosedError):
                await client.connect()
            await eventually(first.closed.is_set)

        assert first.close_code == 1000
        assert first.close_reason == 'shutdown'
        assert stream_tasks() == []

    @pytest.mark.asyncio
    async def test_close_after_goaway_leaves_no_task(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            await fake_router.conns[0].send({
                'type': 'goaway',
                'reason': 'shutdown',
            })
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-1'
                )
            )

            await client.close(1001, 'shutdown')

        assert stream_tasks() == []
