# ruff: noqa: PLR6301, PLR2004 - testes em classe e literais nos asserts, como no
# resto da suíte.
import asyncio
import contextlib
import logging
import signal
import threading
import time
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from chatgraph.logger.user_logger import UserLoggerManager
from chatgraph.stream.consumer import StreamConsumer
from chatgraph.stream.errors import (
    StreamClosedError,
    StreamConfigError,
    StreamRejectedError,
)
from chatgraph.stream.router_client import RouterStreamClient
from chatgraph.stream.runtime import THREAD_NAME
from tests.unit.stream_fake_router import (
    ConnScript,
    ThreadedFakeRouter,
    eventually,
    make_deliver,
)

SYSTEM = 'chatgraph.system'


def io_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == THREAD_NAME]


def stream_tasks() -> list[asyncio.Task]:
    return [
        t
        for t in asyncio.all_tasks()
        if t.get_name().startswith('chatgraph-stream-') and not t.done()
    ]


def messages(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records]


def commands(conn) -> list[dict]:
    return conn.of_type('command')


@pytest_asyncio.fixture(autouse=True)
async def no_leftovers():
    yield
    await eventually(lambda: not io_threads() and not stream_tasks())


@contextlib.asynccontextmanager
async def running(router, settings, handler, **options):
    consumer = StreamConsumer(
        router.url, 'tok-1', ['rh'], _settings=settings, **options
    )
    task = asyncio.create_task(consumer.start_consume(handler))
    try:
        yield consumer, task
    finally:
        if not task.done():
            consumer.request_shutdown()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(task, 5.0)


async def connected(router) -> None:
    await eventually(lambda: router.conns and router.conns[0].welcome_at)
    await asyncio.sleep(0.05)


@pytest.mark.unit
class TestFullTurn:
    @pytest.mark.asyncio
    async def test_deliver_runs_handler_and_commands_go_through_stream(
        self, fake_router, stream_settings
    ):
        seen = []

        async def handler(usercall):
            seen.append(usercall)
            await usercall.send('oi')
            await usercall.set_route('x')

        async with running(fake_router, stream_settings, handler) as (
            consumer,
            task,
        ):
            await connected(fake_router)
            conn = fake_router.conns[0]

            await conn.send(make_deliver('d1', 'm1', text='ola'))
            await eventually(lambda: len(commands(conn)) == 2)
            consumer.request_shutdown()
            await task

        assert isinstance(seen[0]._UserCall__router_client, RouterStreamClient)
        assert seen[0].content_message == 'ola'
        types = [f['type'] for _, f in conn.frames]
        assert types[:2] == ['hello', 'ack']
        assert [f['name'] for f in commands(conn)] == ['send', 'set_route']
        assert commands(conn)[1]['payload'] == {'route': 'x'}
        assert commands(conn)[0]['chat_id'] == {
            'user_id': 'user-1',
            'company_id': 'company-1',
        }

    @pytest.mark.asyncio
    async def test_handler_error_publishes_once_and_worker_continues(
        self, fake_router, stream_settings, monkeypatch
    ):
        removed = []
        monkeypatch.setattr(
            UserLoggerManager,
            'remove_user_logger',
            lambda user_id, company_id: removed.append((user_id, company_id)),
        )
        publisher = MagicMock()
        publisher.publish_error = AsyncMock()
        handled = []

        async def handler(usercall):
            handled.append(usercall.content_message)
            if len(handled) == 1:
                raise RuntimeError('boom')

        async with running(fake_router, stream_settings, handler) as (
            consumer,
            task,
        ):
            consumer.set_log_publisher(publisher)
            await connected(fake_router)
            conn = fake_router.conns[0]

            await conn.send(make_deliver('d1', 'm1', text='um'))
            await conn.send(make_deliver('d2', 'm2', text='dois'))
            await eventually(lambda: len(handled) == 2)
            await eventually(lambda: len(removed) == 2)
            consumer.request_shutdown()
            await task

        assert handled == ['um', 'dois']
        assert publisher.publish_error.await_count == 1
        assert removed == [('user-1', 'company-1')] * 2

    @pytest.mark.asyncio
    async def test_invalid_observation_is_nacked_without_calling_handler(
        self, fake_router, stream_settings
    ):
        handler = AsyncMock()
        frame = make_deliver('d1', 'm1')
        frame['user_state']['observation'] = 'texto'

        async with running(fake_router, stream_settings, handler) as (
            consumer,
            task,
        ):
            await connected(fake_router)
            conn = fake_router.conns[0]

            await conn.send(frame)
            await eventually(lambda: conn.of_type('nack'))
            consumer.request_shutdown()
            await task

        assert conn.of_type('nack') == [
            {
                'type': 'nack',
                'delivery_id': 'd1',
                'msg_id': 'm1',
                'retryable': False,
                'error': 'invalid_observation',
            }
        ]
        handler.assert_not_awaited()


@pytest.mark.unit
class TestBlockingHandler:
    @pytest.mark.asyncio
    async def test_blocking_handler_does_not_delay_the_ack(
        self, stream_settings
    ):
        router = ThreadedFakeRouter()
        router.start()
        handled = []

        async def handler(usercall):
            handled.append(usercall.content_message)
            if len(handled) == 1:
                time.sleep(1.5)

        async def burst(fake):
            conn = fake.conns[0]
            await conn.send(make_deliver('d1', 'm1', text='um'))
            await asyncio.sleep(0.1)
            await conn.send(make_deliver('d2', 'm2', text='dois'))

        consumer = StreamConsumer(
            router.url, 'tok-1', ['rh'], _settings=stream_settings
        )
        task = asyncio.create_task(consumer.start_consume(handler))
        try:
            await eventually(
                lambda: (
                    router.router.conns and router.router.conns[0].welcome_at
                )
            )
            await asyncio.sleep(0.05)
            await asyncio.wrap_future(router.run(burst))

            conn = router.router.conns[0]
            second_sent = next(
                t for t, f in conn.sent if f.get('delivery_id') == 'd2'
            )
            second_ack = next(
                t for t, f in conn.frames if f.get('delivery_id') == 'd2'
            )
            consumer.request_shutdown()
            await asyncio.wait_for(task, 5.0)
        finally:
            router.close()

        assert second_ack - second_sent < 0.5
        assert handled == ['um', 'dois']


@pytest.mark.unit
class TestBoot:
    @pytest.mark.asyncio
    async def test_boot_401_raises_rejected_and_never_runs_handler(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        fake_router.default = ConnScript(status=401)
        handler = AsyncMock()
        consumer = StreamConsumer(
            fake_router.url, 'tok-1', ['rh'], _settings=stream_settings
        )

        with pytest.raises(StreamRejectedError, match='401 unauthorized'):
            await asyncio.wait_for(consumer.start_consume(handler), 5.0)

        assert any(
            'Message receiver connect failed err=StreamRejectedError' in m
            for m in messages(caplog)
        )
        handler.assert_not_awaited()
        assert io_threads() == []

    @pytest.mark.asyncio
    async def test_shutdown_during_boot_raises_closed_with_error_log(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        fake_router.default = ConnScript(status=503)
        handler = AsyncMock()
        consumer = StreamConsumer(
            fake_router.url, 'tok-1', ['rh'], _settings=stream_settings
        )
        task = asyncio.create_task(consumer.start_consume(handler))
        await asyncio.sleep(0.1)

        consumer.request_shutdown()

        with pytest.raises(
            StreamClosedError, match='shutdown antes do welcome'
        ):
            await asyncio.wait_for(task, 5.0)
        error = [
            r
            for r in caplog.records
            if 'Message receiver connect failed' in r.getMessage()
        ]
        assert [r.levelno for r in error] == [logging.ERROR]
        assert 'StreamClosedError: shutdown antes do welcome' in (
            error[0].getMessage()
        )
        handler.assert_not_awaited()
        assert io_threads() == []

    @pytest.mark.asyncio
    async def test_boot_failure_does_not_log_task_crash(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        fake_router.default = ConnScript(status=401)
        consumer = StreamConsumer(
            fake_router.url, 'tok-1', ['rh'], _settings=stream_settings
        )

        with pytest.raises(StreamRejectedError):
            await asyncio.wait_for(consumer.start_consume(AsyncMock()), 5.0)

        assert not any('Stream task crashed' in m for m in messages(caplog))

    @pytest.mark.asyncio
    async def test_logs_transport_mode_and_menus(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        async with running(fake_router, stream_settings, AsyncMock()) as (
            consumer,
            task,
        ):
            await connected(fake_router)
            consumer.request_shutdown()
            await task

        assert "Router transport mode=stream menus=['rh']" in messages(caplog)


@pytest.mark.unit
class TestShutdown:
    @pytest.mark.asyncio
    async def test_clean_shutdown_drains_queue_and_closes_1000(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        handled = []

        async def handler(usercall):
            await asyncio.sleep(0.2)
            handled.append(usercall.content_message)

        async with running(fake_router, stream_settings, handler) as (
            consumer,
            task,
        ):
            await connected(fake_router)
            conn = fake_router.conns[0]
            await conn.send(make_deliver('d1', 'm1', text='um'))
            await conn.send(make_deliver('d2', 'm2', text='dois'))
            await eventually(lambda: len(conn.of_type('ack')) == 2)

            consumer.request_shutdown()
            await eventually(
                lambda: any('Stream draining' in m for m in messages(caplog))
            )
            await conn.send(make_deliver('d3', 'm3', text='tres'))
            await eventually(lambda: conn.of_type('nack'))
            await asyncio.wait_for(task, 5.0)
            await eventually(conn.closed.is_set)

        assert task.exception() is None
        assert handled == ['um', 'dois']
        assert conn.of_type('nack')[0]['error'] == 'draining'
        assert conn.of_type('nack')[0]['retryable'] is True
        assert conn.close_code == 1000
        ordered = [
            next(i for i, m in enumerate(messages(caplog)) if text in m)
            for text in (
                'Stream draining',
                'Message receiver drained',
                'Stream closed',
            )
        ]
        assert ordered == sorted(ordered)

    @pytest.mark.asyncio
    async def test_drain_timeout_discards_and_closes_1001(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        never = asyncio.Event()
        started = []

        async def handler(usercall):
            started.append(True)
            await never.wait()

        async with running(
            fake_router, stream_settings, handler, drain_timeout=0.1
        ) as (consumer, task):
            await connected(fake_router)
            conn = fake_router.conns[0]
            await conn.send(make_deliver('d1', 'm1'))
            await eventually(lambda: started)

            began = asyncio.get_running_loop().time()
            consumer.request_shutdown()
            await asyncio.wait_for(task, 1.0)
            elapsed = asyncio.get_running_loop().time() - began
            await eventually(conn.closed.is_set)

        assert elapsed < 1.0
        assert 'Stream drain timeout discarded=1' in messages(caplog)
        assert conn.close_code == 1001
        assert not any(
            'Message receiver drained' in m for m in messages(caplog)
        )

    @pytest.mark.asyncio
    async def test_drain_timeout_with_swallowed_cancel_still_returns(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        started = []

        async def handler(usercall):
            started.append(True)
            try:
                await asyncio.Event().wait()
            except BaseException:
                pass

        async with running(
            fake_router, stream_settings, handler, drain_timeout=0.1
        ) as (consumer, task):
            await connected(fake_router)
            conn = fake_router.conns[0]
            await conn.send(make_deliver('d1', 'm1'))
            await eventually(lambda: started)

            consumer.request_shutdown()
            await asyncio.wait_for(task, 1.0)
            await eventually(conn.closed.is_set)

        assert 'Stream drain timeout discarded=1' in messages(caplog)
        assert conn.close_code == 1001

    @pytest.mark.asyncio
    async def test_request_shutdown_before_start_consume_ends_it_promptly(
        self, fake_router, stream_settings
    ):
        consumer = StreamConsumer(
            fake_router.url, 'tok-1', ['rh'], _settings=stream_settings
        )
        consumer.request_shutdown()

        with pytest.raises(StreamClosedError):
            await asyncio.wait_for(consumer.start_consume(AsyncMock()), 5.0)

    @pytest.mark.asyncio
    async def test_signal_handlers_are_registered_and_removed(
        self, fake_router, stream_settings, monkeypatch
    ):
        loop = asyncio.get_running_loop()
        added = []
        removed = []
        monkeypatch.setattr(
            loop,
            'add_signal_handler',
            lambda sig, callback: added.append((sig, callback)),
        )
        monkeypatch.setattr(loop, 'remove_signal_handler', removed.append)

        async with running(fake_router, stream_settings, AsyncMock()) as (
            consumer,
            task,
        ):
            await connected(fake_router)
            assert added == [
                (signal.SIGINT, consumer.request_shutdown),
                (signal.SIGTERM, consumer.request_shutdown),
            ]
            assert removed == []

            consumer.request_shutdown()
            assert removed == [signal.SIGINT, signal.SIGTERM]
            await task

        assert removed == [signal.SIGINT, signal.SIGTERM]

    @pytest.mark.asyncio
    async def test_missing_signal_support_only_warns(
        self, fake_router, stream_settings, monkeypatch, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)

        def unsupported(sig, callback):
            raise NotImplementedError

        monkeypatch.setattr(
            asyncio.get_running_loop(), 'add_signal_handler', unsupported
        )

        async with running(fake_router, stream_settings, AsyncMock()) as (
            consumer,
            task,
        ):
            await connected(fake_router)
            consumer.request_shutdown()
            await task

        assert any(
            'signal handlers unavailable' in m for m in messages(caplog)
        )


@pytest.mark.unit
class TestConsumerContract:
    @pytest.mark.asyncio
    async def test_cleanup_closes_router_client_if_any(
        self, fake_router, stream_settings
    ):
        consumer = StreamConsumer(
            fake_router.url, 'tok-1', ['rh'], _settings=stream_settings
        )

        await consumer.cleanup()

    def test_construction_validates_without_connecting(self):
        with pytest.raises(StreamConfigError):
            StreamConsumer('http://r:8085', ' ', ['rh'])
        assert io_threads() == []

    def test_reprer_hides_the_token(self, capsys):
        consumer = StreamConsumer('http://r:8085', 'segredo', ['rh', 'geral'])

        consumer.reprer()

        out = capsys.readouterr().out
        assert 'ws://r:8085/v1/menus/connect' in out
        assert 'segredo' not in out
        assert 'stream' in out


@pytest.mark.unit
class TestLoadDotenv:
    ALL = (
        'ROUTER_URL',
        'ROUTER_TOKEN',
        'ROUTER_MENUS',
        'RABBIT_QUEUE',
        'RABBIT_USER',
        'RABBIT_PASS',
        'RABBIT_URI',
    )

    @pytest.fixture(autouse=True)
    def clean_env(self, monkeypatch):
        for name in self.ALL:
            monkeypatch.delenv(name, raising=False)

    @pytest.mark.parametrize(
        ('env', 'menus'),
        [
            ({'ROUTER_MENUS': ' rh, geral ,rh,'}, ('rh', 'geral')),
            ({'RABBIT_QUEUE': 'rh'}, ('rh',)),
            (
                {'ROUTER_MENUS': 'financeiro', 'RABBIT_QUEUE': 'rh'},
                ('financeiro',),
            ),
        ],
        ids=['menus_normalized', 'queue_fallback', 'menus_win_over_queue'],
    )
    def test_menus(self, monkeypatch, env, menus):
        monkeypatch.setenv('ROUTER_URL', 'http://router:8085')
        monkeypatch.setenv('ROUTER_TOKEN', 'tok')
        for name, value in env.items():
            monkeypatch.setenv(name, value)

        consumer = StreamConsumer.load_dotenv()

        assert consumer._options.menus == menus
        assert consumer._options.router_url == 'http://router:8085'
        assert consumer._options.token == 'tok'

    @pytest.mark.parametrize(
        ('env', 'missing'),
        [
            (
                {'ROUTER_URL': 'http://r', 'ROUTER_TOKEN': 'tok'},
                'ROUTER_MENUS',
            ),
            ({'ROUTER_URL': 'http://r', 'ROUTER_MENUS': 'rh'}, 'ROUTER_TOKEN'),
            ({'ROUTER_TOKEN': 'tok', 'ROUTER_MENUS': 'rh'}, 'ROUTER_URL'),
        ],
        ids=['no_menus', 'no_token', 'no_url'],
    )
    def test_missing_variable_is_named(self, monkeypatch, env, missing):
        for name, value in env.items():
            monkeypatch.setenv(name, value)

        with pytest.raises(ValueError, match='Corrija as variáveis') as info:
            StreamConsumer.load_dotenv()

        assert missing in str(info.value)

    def test_invalid_scheme_raises_config_error(self, monkeypatch):
        monkeypatch.setenv('ROUTER_URL', 'ftp://router')
        monkeypatch.setenv('ROUTER_TOKEN', 'tok')
        monkeypatch.setenv('ROUTER_MENUS', 'rh')

        with pytest.raises(StreamConfigError):
            StreamConsumer.load_dotenv()

    def test_host_only_url_is_accepted(self, monkeypatch):
        monkeypatch.setenv('ROUTER_URL', 'http://router:8085')
        monkeypatch.setenv('ROUTER_TOKEN', 'tok')
        monkeypatch.setenv('ROUTER_MENUS', 'rh')

        assert StreamConsumer.load_dotenv() is not None

    def test_rabbit_variables_are_not_required(self, monkeypatch):
        monkeypatch.setenv('ROUTER_URL', 'http://router:8085')
        monkeypatch.setenv('ROUTER_TOKEN', 'tok')
        monkeypatch.setenv('ROUTER_MENUS', 'rh')

        consumer = StreamConsumer.load_dotenv()

        assert consumer._options.menus == ('rh',)
