# ruff: noqa: PLR6301, PLR2004 - testes em classe e literais nos asserts, como no
# resto da suíte.
import asyncio
import contextlib
import json
import logging
import os
import signal
import sys
import textwrap
import threading
from pathlib import Path
from unittest.mock import MagicMock

import aio_pika
import aio_pika.message
import httpx
import pytest
import pytest_asyncio

from chatgraph.auth.credentials import Credential
from chatgraph.messages.message_consumer import MessageConsumer
from chatgraph.messages.transport import (
    TRANSPORT_DUAL,
    consumer_from_env,
    read_transport,
)
from chatgraph.stream.consumer import StreamConsumer
from chatgraph.stream.dual import DualConsumer
from chatgraph.stream.errors import StreamRejectedError
from chatgraph.stream.runtime import THREAD_NAME
from tests.unit.stream_fake_router import (
    ConnScript,
    eventually,
    make_deliver,
    stream_client,
)

SYSTEM = 'chatgraph.system'
REPO_ROOT = str(Path(__file__).resolve().parents[2])

ENV_NAMES = (
    'ROUTER_TRANSPORT',
    'ROUTER_URL',
    'ROUTER_TOKEN',
    'ROUTER_MENUS',
    'RABBIT_USER',
    'RABBIT_PASS',
    'RABBIT_URI',
    'RABBIT_QUEUE',
    'LOG_RABBIT_QUEUE',
)


def system_messages(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == SYSTEM]


def io_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == THREAD_NAME]


def stream_tasks() -> list[asyncio.Task]:
    return [
        t
        for t in asyncio.all_tasks()
        if t.get_name().startswith('chatgraph-stream-') and not t.done()
    ]


@pytest.fixture
def dual_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('ROUTER_TRANSPORT', 'dual')
    monkeypatch.setenv('ROUTER_URL', 'http://r:8085')
    monkeypatch.setenv('ROUTER_TOKEN', 'tok')
    monkeypatch.setenv('RABBIT_USER', 'user')
    monkeypatch.setenv('RABBIT_PASS', 'pass')
    monkeypatch.setenv('RABBIT_URI', 'rabbit:5672')
    monkeypatch.setenv('RABBIT_QUEUE', 'rh')


@pytest.mark.unit
class TestTransportSelection:
    @pytest.mark.parametrize('value', ['dual', ' DUAL ', 'Dual'])
    def test_read_transport_accepts_dual(self, monkeypatch, value):
        monkeypatch.setenv('ROUTER_TRANSPORT', value)

        assert read_transport() == TRANSPORT_DUAL

    @pytest.mark.parametrize('value', ['ws', 'hibrido'])
    def test_invalid_value_names_the_three_transports(
        self, monkeypatch, value
    ):
        monkeypatch.setenv('ROUTER_TRANSPORT', value)

        with pytest.raises(ValueError, match='use queue, stream ou dual'):
            read_transport()

    def test_consumer_from_env_builds_dual_consumer_without_network(
        self, dual_env
    ):
        consumer = consumer_from_env()

        assert isinstance(consumer, DualConsumer)
        assert io_threads() == []

    def test_dual_consumer_parts_follow_the_dual_contract(self, dual_env):
        consumer = DualConsumer.load_dotenv()

        options = consumer._stream._options
        assert isinstance(consumer._queue, MessageConsumer)
        assert options.mode == 'dual'
        assert options.tolerant is True
        assert options.menus == ('rh',)
        assert consumer._stream._actions_via_http is True

    def test_dual_requires_the_rabbit_variables(self, dual_env, monkeypatch):
        monkeypatch.delenv('RABBIT_USER')

        with pytest.raises(ValueError, match='RABBIT_USER'):
            DualConsumer.load_dotenv()

    def test_history_store_and_log_publisher_reach_both_consumers(self):
        queue, stream = MagicMock(), MagicMock()
        consumer = DualConsumer(queue, stream)
        store, publisher = object(), object()

        consumer.set_history_store(store)
        consumer.set_log_publisher(publisher)

        queue.set_history_store.assert_called_once_with(store)
        stream.set_history_store.assert_called_once_with(store)
        queue.set_log_publisher.assert_called_once_with(publisher)
        stream.set_log_publisher.assert_called_once_with(publisher)


@pytest.mark.unit
class TestClientHello:
    @pytest.mark.asyncio
    async def test_dual_mode_is_sent_in_the_hello(
        self, fake_router, stream_settings
    ):
        async with stream_client(
            fake_router, stream_settings, mode='dual'
        ) as (client, _):
            await client.connect()
            await eventually(lambda: client._current is not None)

        hello = fake_router.conns[0].frames[0][1]
        assert hello['mode'] == 'dual'

    @pytest.mark.asyncio
    async def test_hello_without_mode_has_no_mode_key(
        self, fake_router, stream_settings
    ):
        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()

        assert 'mode' not in fake_router.conns[0].frames[0][1]


@pytest.mark.unit
class TestClientWelcomeTransport:
    @pytest.mark.asyncio
    async def test_queue_transport_logs_idle_once_and_stays_connected(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        fake_router.default = ConnScript(transport='queue', heartbeat_s=1)

        async with stream_client(
            fake_router, stream_settings, mode='dual'
        ) as (client, _):
            await client.connect()
            await eventually(lambda: client._current is not None)
            conn = fake_router.conns[0]
            await eventually(lambda: len(conn.of_type('ping')) >= 3)

            assert client._current is not None
            assert not client._current.closed.is_set()

        messages = system_messages(caplog)
        idle = [
            m for m in messages if 'Stream idle: router in queue mode' in m
        ]
        assert len(idle) == 1
        assert len(fake_router.attempts) == 1
        assert any(
            'Stream connected' in m and 'router_transport=queue' in m
            for m in messages
        )

    @pytest.mark.asyncio
    async def test_stream_transport_has_no_idle_log(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        fake_router.default = ConnScript(transport='stream')

        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            await eventually(lambda: client._current is not None)

        messages = system_messages(caplog)
        assert not any('Stream idle' in m for m in messages)
        assert any('router_transport=stream' in m for m in messages)

    @pytest.mark.asyncio
    async def test_welcome_without_transport_has_no_idle_log(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)

        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            await eventually(lambda: client._current is not None)

        assert not any('Stream idle' in m for m in system_messages(caplog))

    @pytest.mark.asyncio
    async def test_idle_log_is_emitted_again_for_the_replacement_connection(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        fake_router.default = ConnScript(transport='queue')

        async with stream_client(fake_router, stream_settings) as (client, _):
            await client.connect()
            await eventually(lambda: client._current is not None)
            await fake_router.conns[0].send({'type': 'goaway', 'reason': 'x'})
            await eventually(lambda: len(fake_router.conns) == 2)
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-1'
                )
            )

        idle = [
            m
            for m in system_messages(caplog)
            if 'Stream idle: router in queue mode' in m
        ]
        assert len(idle) == 2


@pytest.mark.unit
class TestClientTolerant:
    @pytest.mark.asyncio
    async def test_404_twice_then_accepts_warns_only_once(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        not_found = ConnScript(status=404)
        fake_router.scripts = [not_found, not_found, ConnScript()]

        async with stream_client(
            fake_router, stream_settings, tolerant=True, mode='dual'
        ) as (client, _):
            await asyncio.wait_for(client.connect(), 1.0)
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-2'
                )
            )

        records = [r for r in caplog.records if r.name == SYSTEM]
        not_found_logs = [
            r
            for r in records
            if 'Stream router has no stream endpoint (404)' in r.getMessage()
        ]
        assert [r.levelno for r in not_found_logs] == [
            logging.WARNING,
            logging.DEBUG,
        ]
        assert not [r for r in records if r.levelno >= logging.ERROR]
        assert len(fake_router.attempts) == 3

    @pytest.mark.asyncio
    async def test_404_sequence_warns_again_after_a_connection_succeeded(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        not_found = ConnScript(status=404)
        fake_router.scripts = [
            not_found,
            ConnScript(abort_after_welcome=True),
            not_found,
            ConnScript(),
        ]

        async with stream_client(
            fake_router, stream_settings, tolerant=True
        ) as (client, _):
            await client.connect()
            await eventually(
                lambda: (
                    client._current is not None
                    and client._current.id == 'conn-3'
                )
            )

        warnings = [
            r
            for r in caplog.records
            if r.levelno == logging.WARNING
            and 'no stream endpoint (404)' in r.getMessage()
        ]
        assert len(warnings) == 2

    @pytest.mark.asyncio
    async def test_404_retries_at_the_long_delay(
        self, fake_router, stream_settings
    ):
        stream_settings.auth_retry_delay = 0.15
        fake_router.default = ConnScript(status=404)

        async with stream_client(
            fake_router, stream_settings, tolerant=True
        ) as (client, _):
            await client.connect()
            await eventually(lambda: len(fake_router.attempts) >= 3)

        first, second, third = (a.at for a in fake_router.attempts[:3])
        assert second - first >= 0.14
        assert third - second >= 0.14

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'script',
        [
            ConnScript(status=401),
            ConnScript(status=403),
            ConnScript(close_after_hello=(1008, 'router_in_queue_mode')),
        ],
        ids=['401', '403', '1008_router_in_queue_mode'],
    )
    async def test_rejection_logs_error_per_attempt_and_never_raises(
        self, fake_router, stream_settings, caplog, script
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        fake_router.default = script

        async with stream_client(
            fake_router, stream_settings, tolerant=True, mode='dual'
        ) as (client, _):
            await asyncio.wait_for(client.connect(), 1.0)
            await eventually(lambda: len(fake_router.attempts) >= 4)

        errors = [
            r
            for r in caplog.records
            if r.name == SYSTEM
            and r.levelno == logging.ERROR
            and 'Stream rejected, retrying' in r.getMessage()
        ]
        assert len(errors) >= 3
        assert not any(
            'no stream endpoint' in r.getMessage() for r in caplog.records
        )

    @pytest.mark.asyncio
    async def test_503_uses_the_normal_backoff_without_error(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        fake_router.scripts = [
            ConnScript(status=503, body='{"error":"draining"}'),
            ConnScript(),
        ]

        async with stream_client(
            fake_router, stream_settings, tolerant=True
        ) as (client, _):
            await client.connect()
            await eventually(lambda: client._current is not None)

        records = [r for r in caplog.records if r.name == SYSTEM]
        assert any(
            r.levelno == logging.INFO and 'class=short' in r.getMessage()
            for r in records
        )
        assert not [r for r in records if r.levelno >= logging.ERROR]

    @pytest.mark.asyncio
    async def test_not_tolerant_router_in_queue_mode_is_a_boot_rejection(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(
            close_after_hello=(1008, 'router_in_queue_mode')
        )

        async with stream_client(fake_router, stream_settings) as (client, _):
            with pytest.raises(
                StreamRejectedError, match='1008 router_in_queue_mode'
            ):
                await asyncio.wait_for(client.connect(), 2.0)

        assert len(fake_router.attempts) == 1


class FakeQueueConsumer:
    def __init__(self, fail_with: Exception | None = None) -> None:
        self.process = None
        self.started = asyncio.Event()
        self.cancelled = False
        self.cleaned = 0
        self.history_store = None
        self.log_publisher = None
        self.fail = asyncio.Event()
        self._fail_with = fail_with
        self._inbox: asyncio.Queue = asyncio.Queue()

    def feed(self, usercall) -> None:
        self._inbox.put_nowait(usercall)

    async def start_consume(self, process_message) -> None:
        self.started.set()
        try:
            while True:
                if self._fail_with is not None:
                    await self.fail.wait()
                    raise self._fail_with
                usercall = await self._inbox.get()
                await process_message(usercall)
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def cleanup(self) -> None:
        self.cleaned += 1

    def reprer(self) -> None:
        pass


class FakeAmqpMessage:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.processed = False
        self.redelivered = False
        self.channel = MagicMock(is_closed=False)
        self.acks = 0
        self.rejects: list[bool] = []

    def process(self, **kwargs):
        return aio_pika.message.IncomingMessage.process(self, **kwargs)

    async def ack(self) -> None:
        self.acks += 1

    async def reject(self, requeue: bool = False) -> None:
        self.rejects.append(requeue)


class FakeAmqpQueue:
    def __init__(self, message: FakeAmqpMessage, gate: asyncio.Event) -> None:
        self._message = message
        self._gate = gate

    async def bind(self, **kwargs) -> None:
        pass

    async def __aiter__(self):
        await self._gate.wait()
        yield self._message
        await asyncio.Event().wait()


class FakeAmqpChannel:
    def __init__(self, queue: FakeAmqpQueue) -> None:
        self._queue = queue

    async def set_qos(self, **kwargs) -> None:
        pass

    async def declare_queue(self, *args, **kwargs) -> FakeAmqpQueue:
        return self._queue


class FakeAmqpConnection:
    def __init__(self, queue: FakeAmqpQueue) -> None:
        self._queue = queue

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc) -> None:
        pass

    async def channel(self) -> FakeAmqpChannel:
        return FakeAmqpChannel(self._queue)


def dual_stream_consumer(router, settings) -> StreamConsumer:
    return StreamConsumer(
        router.url,
        'tok-1',
        ['rh'],
        tolerant=True,
        mode='dual',
        actions_via_http=True,
        _settings=settings,
    )


@pytest_asyncio.fixture
async def no_leftovers():
    yield
    await eventually(lambda: not io_threads() and not stream_tasks())


@contextlib.asynccontextmanager
async def running(queue, stream, handler):
    consumer = DualConsumer(queue, stream)
    task = asyncio.create_task(consumer.start_consume(handler))
    try:
        yield consumer, task
    finally:
        if not task.done():
            stream.request_shutdown()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(task, 5.0)


@pytest.mark.unit
@pytest.mark.usefixtures('no_leftovers')
class TestDualConsumer:
    @pytest.mark.asyncio
    async def test_queue_and_stream_messages_use_the_same_process_message(
        self, fake_router, stream_settings
    ):
        handled = []

        async def handler(usercall):
            handled.append(usercall.content_message)

        queue = FakeQueueConsumer()
        stream = dual_stream_consumer(fake_router, stream_settings)

        async with running(queue, stream, handler) as (_, task):
            await eventually(lambda: fake_router.conns)
            await eventually(lambda: fake_router.conns[0].welcome_at)
            await asyncio.sleep(0.05)
            queue.feed(MagicMock(content_message='da fila'))
            await eventually(lambda: handled == ['da fila'])
            await fake_router.conns[0].send(
                make_deliver('d1', 'm1', text='do stream')
            )
            await eventually(lambda: len(handled) == 2)
            stream.request_shutdown()
            await asyncio.wait_for(task, 5.0)

        assert handled == ['da fila', 'do stream']
        assert fake_router.conns[0].frames[0][1]['mode'] == 'dual'

    @pytest.mark.asyncio
    async def test_both_tasks_are_named(self, fake_router, stream_settings):
        queue = FakeQueueConsumer()
        stream = dual_stream_consumer(fake_router, stream_settings)

        async with running(queue, stream, MagicMock()) as (_, task):
            await asyncio.wait_for(queue.started.wait(), 2.0)
            await eventually(lambda: fake_router.conns)
            names = {t.get_name() for t in stream_tasks()}
            stream.request_shutdown()
            await asyncio.wait_for(task, 5.0)

        assert {
            'chatgraph-stream-dual-queue',
            'chatgraph-stream-dual-stream',
        } <= names

    @pytest.mark.asyncio
    async def test_send_from_a_stream_message_goes_over_http_not_ws(
        self, fake_router, stream_settings, respx_mock
    ):
        route = respx_mock.post(
            f'{fake_router.url}/v1/actions/messages/send/'
        ).mock(
            return_value=httpx.Response(
                200, json={'status': True, 'message': 'ok'}
            )
        )
        sent = []

        async def handler(usercall):
            await usercall.send('resposta')
            sent.append(usercall.content_message)

        queue = FakeQueueConsumer()
        stream = dual_stream_consumer(fake_router, stream_settings)

        async with running(queue, stream, handler) as (_, task):
            await eventually(lambda: fake_router.conns)
            await eventually(lambda: fake_router.conns[0].welcome_at)
            await asyncio.sleep(0.05)
            conn = fake_router.conns[0]
            await conn.send(make_deliver('d1', 'm1', text='oi'))
            await eventually(lambda: sent == ['oi'])
            stream.request_shutdown()
            await asyncio.wait_for(task, 5.0)

        assert route.call_count == 1
        assert conn.of_type('command') == []

    @pytest.mark.asyncio
    async def test_stream_drain_cancels_the_queue_task_and_returns(
        self, fake_router, stream_settings, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=SYSTEM)
        queue = FakeQueueConsumer()
        stream = dual_stream_consumer(fake_router, stream_settings)
        consumer = DualConsumer(queue, stream)
        task = asyncio.create_task(consumer.start_consume(MagicMock()))
        await asyncio.wait_for(queue.started.wait(), 2.0)
        await eventually(lambda: fake_router.conns)
        await asyncio.sleep(0.05)

        stream.request_shutdown()
        await asyncio.wait_for(task, 5.0)

        assert queue.cancelled is True
        assert queue.cleaned >= 1
        messages = system_messages(caplog)
        assert 'Message receiver drained' in messages
        assert 'Stream closed' in messages
        assert any('mode=dual' in m for m in messages)

    @pytest.mark.asyncio
    async def test_queue_failure_cancels_the_stream_and_raises(
        self, fake_router, stream_settings
    ):
        queue = FakeQueueConsumer(fail_with=RuntimeError('fila caiu'))
        stream = dual_stream_consumer(fake_router, stream_settings)
        consumer = DualConsumer(queue, stream)
        task = asyncio.create_task(consumer.start_consume(MagicMock()))
        await eventually(
            lambda: fake_router.conns and fake_router.conns[0].welcome_at
        )
        await eventually(
            lambda: (
                stream._client is not None
                and stream._client._current is not None
            )
        )

        queue.fail.set()

        with pytest.raises(RuntimeError, match='fila caiu'):
            await asyncio.wait_for(task, 5.0)
        await eventually(fake_router.conns[0].closed.is_set)
        assert fake_router.conns[0].close_code == 1000
        assert queue.cleaned >= 1

    @pytest.mark.asyncio
    async def test_queue_turn_in_flight_at_shutdown_is_requeued_not_dead_lettered(  # noqa: E501
        self, fake_router, stream_settings, monkeypatch
    ):
        fake_router.default = ConnScript(transport='queue')
        message = FakeAmqpMessage(
            json.dumps(make_deliver('d1', 'm1', text='x')).encode()
        )
        gate = asyncio.Event()
        connection = FakeAmqpConnection(FakeAmqpQueue(message, gate))

        async def connect_robust(*args, **kwargs):
            return connection

        monkeypatch.setattr(aio_pika, 'connect_robust', connect_robust)
        started = asyncio.Event()

        async def handler(usercall):
            started.set()
            await asyncio.Event().wait()

        queue = MessageConsumer(
            Credential(username='u', password='p'),
            'rabbit:5672',
            'http://r:8085',
            'tok',
            'rh',
        )
        stream = dual_stream_consumer(fake_router, stream_settings)

        async with running(queue, stream, handler) as (_, task):
            await eventually(
                lambda: fake_router.conns and fake_router.conns[0].welcome_at
            )
            gate.set()
            await asyncio.wait_for(started.wait(), 2.0)

            stream.request_shutdown()
            await asyncio.wait_for(task, 5.0)

        assert message.rejects == [True]
        assert message.acks == 0

    @pytest.mark.asyncio
    async def test_stream_works_while_router_has_no_stream_endpoint(
        self, fake_router, stream_settings
    ):
        fake_router.default = ConnScript(status=404)
        handled = []

        async def handler(usercall):
            handled.append(usercall.content_message)

        queue = FakeQueueConsumer()
        stream = dual_stream_consumer(fake_router, stream_settings)

        async with running(queue, stream, handler) as (_, task):
            await asyncio.wait_for(queue.started.wait(), 2.0)
            await eventually(lambda: len(fake_router.attempts) >= 2)
            queue.feed(MagicMock(content_message='da fila'))
            await eventually(lambda: handled == ['da fila'])
            assert not task.done()
            stream.request_shutdown()
            await asyncio.wait_for(task, 5.0)


REAL_PROCESS_SCRIPT = textwrap.dedent(
    """
    import asyncio
    import sys

    from chatgraph.stream.consumer import StreamConsumer
    from chatgraph.stream.dual import DualConsumer


    class Queue:
        async def start_consume(self, process_message):
            print('MARK queue started', flush=True)
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                print('MARK queue cancelled', flush=True)
                raise

        async def cleanup(self):
            print('MARK queue cleanup', flush=True)


    async def main():
        stream = StreamConsumer(
            sys.argv[1],
            'tok-1',
            ['rh'],
            tolerant=True,
            mode='dual',
            actions_via_http=True,
        )
        dual = DualConsumer(Queue(), stream)

        async def process_message(usercall):
            print('MARK turn ' + usercall.content_message, flush=True)

        await dual.start_consume(process_message)
        print('MARK returned', flush=True)


    asyncio.run(main())
    """
)


async def read_until(proc, marker: str, timeout: float = 10.0) -> list[str]:
    lines: list[str] = []

    async def reader() -> None:
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                return
            line = raw.decode().rstrip()
            lines.append(line)
            if marker in line:
                return

    await asyncio.wait_for(reader(), timeout)
    return lines


@pytest.mark.unit
class TestRealProcessSignal:
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        sys.platform == 'win32', reason='SIGTERM de processo só em POSIX'
    )
    async def test_sigterm_in_a_real_process_exits_zero_with_both_tasks_done(
        self, fake_router, tmp_path
    ):
        script = tmp_path / 'dual_bot.py'
        script.write_text(REAL_PROCESS_SCRIPT)
        env = {
            **os.environ,
            'PYTHONPATH': REPO_ROOT,
            'CHATGRAPH_LOG_LEVEL': 'INFO',
        }
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script),
            fake_router.url,
            cwd=tmp_path,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        output: list[str] = []
        try:
            await eventually(lambda: fake_router.conns, timeout=10.0)
            await eventually(lambda: fake_router.conns[0].welcome_at)
            await asyncio.sleep(0.2)
            await fake_router.conns[0].send(
                make_deliver('d1', 'm1', text='oi')
            )
            output += await read_until(proc, 'MARK turn oi')

            proc.send_signal(signal.SIGTERM)
            rest, _ = await asyncio.wait_for(proc.communicate(), 20.0)
            output += rest.decode().splitlines()
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()

        text = '\n'.join(output)
        assert proc.returncode == 0, text
        assert 'MARK queue cancelled' in text
        assert 'MARK queue cleanup' in text
        assert 'Message receiver drained' in text
        assert 'Stream closed' in text
        assert 'MARK returned' in text
        await eventually(fake_router.conns[0].closed.is_set)
        assert fake_router.conns[0].close_code == 1000
