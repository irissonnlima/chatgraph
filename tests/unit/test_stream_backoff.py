# ruff: noqa: PLR2004, PLR6301 - testes em classe e literais nos asserts, como no
# resto da suíte.
import asyncio

import pytest
from websockets.asyncio.client import connect
from websockets.exceptions import (
    ConnectionClosed,
    InvalidHandshake,
    InvalidMessage,
    InvalidStatus,
)

from chatgraph.stream import frames
from chatgraph.stream.backoff import (
    FailureClass,
    classify,
    failure_detail,
    full_jitter,
)
from chatgraph.stream.options import connect_url
from tests.unit.stream_fake_router import ConnScript, FakeRouter


def ceiling(value: float) -> float:
    return value


async def handshake_error(url: str, read_timeout: float = 1.0) -> Exception:
    """Faz o handshake até falhar e devolve a exceção real do websockets."""
    ws = None
    try:
        ws = await connect(
            connect_url(url),
            open_timeout=1.0,
            ping_interval=None,
            close_timeout=0.2,
        )
        await ws.send(frames.encode(frames.hello(['rh'], 1)))
        while True:
            await asyncio.wait_for(ws.recv(), read_timeout)
    except Exception as exc:
        return exc
    finally:
        if ws is not None:
            await ws.close()


@pytest.mark.unit
class TestFullJitter:
    @pytest.mark.parametrize(
        ('attempt', 'expected'),
        [(0, 0.5), (3, 4.0), (10, 30.0), (64, 30.0)],
    )
    def test_ceiling_grows_until_cap(self, attempt, expected):
        assert full_jitter(attempt, 0.5, 30.0, ceiling) == expected

    def test_short_cap_is_respected(self):
        assert full_jitter(10, 0.5, 5.0, ceiling) == 5.0

    def test_rand_zero_gives_zero(self):
        assert full_jitter(5, 0.5, 30.0, lambda _: 0) == 0


@pytest.mark.unit
class TestClassify:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ('script', 'expected'),
        [
            (ConnScript(status=401), FailureClass.CONFIG),
            (ConnScript(status=403), FailureClass.CONFIG),
            (ConnScript(status=404), FailureClass.CONFIG),
            (ConnScript(status=503, body='x'), FailureClass.SHORT),
            (ConnScript(status=500), FailureClass.NETWORK),
            (ConnScript(status=200), FailureClass.NETWORK),
            (
                ConnScript(close_after_hello=(1008, 'menu_not_allowed: rh')),
                FailureClass.CONFIG,
            ),
            (
                ConnScript(close_after_hello=(1013, 'draining')),
                FailureClass.SHORT,
            ),
            (
                ConnScript(close_after_hello=(1011, 'boom')),
                FailureClass.NETWORK,
            ),
            (ConnScript(abort_after_welcome=True), FailureClass.NETWORK),
        ],
    )
    async def test_real_handshake_failures(self, script, expected):
        router = FakeRouter(default=script)
        await router.start()
        try:
            exc = await handshake_error(router.url)
        finally:
            await router.close()

        assert isinstance(exc, (InvalidStatus, ConnectionClosed))
        assert classify(exc) is expected

    @pytest.mark.asyncio
    async def test_connection_refused_is_network(self):
        router = FakeRouter()
        await router.start()
        url = router.url
        await router.close()

        exc = await handshake_error(url)

        assert isinstance(exc, OSError)
        assert classify(exc) is FailureClass.NETWORK

    @pytest.mark.asyncio
    async def test_welcome_timeout_is_network(self):
        router = FakeRouter(default=ConnScript(welcome_delay=0.5))
        await router.start()
        try:
            exc = await handshake_error(router.url, read_timeout=0.05)
        finally:
            await router.close()

        assert isinstance(exc, TimeoutError)
        assert classify(exc) is FailureClass.NETWORK

    @pytest.mark.asyncio
    async def test_garbage_response_is_network(self):
        async def garbage(reader, writer):
            await reader.readuntil(b'\r\n\r\n')
            writer.write(b'nonsense\r\n\r\n')
            await writer.drain()
            writer.close()

        server = await asyncio.start_server(garbage, '127.0.0.1', 0)
        port = server.sockets[0].getsockname()[1]
        try:
            exc = await handshake_error(f'http://127.0.0.1:{port}')
        finally:
            server.close()
            await server.wait_closed()

        assert isinstance(exc, (InvalidMessage, InvalidHandshake))
        assert classify(exc) is FailureClass.NETWORK


@pytest.mark.unit
class TestFailureDetail:
    @pytest.mark.asyncio
    async def test_status_detail_carries_body(self):
        router = FakeRouter(
            default=ConnScript(status=503, body='{"error":"draining"}')
        )
        await router.start()
        try:
            exc = await handshake_error(router.url)
        finally:
            await router.close()

        assert failure_detail(exc) == (
            'status=503 reason={"error":"draining"}'
        )

    @pytest.mark.asyncio
    async def test_close_detail_carries_code_and_reason(self):
        router = FakeRouter(
            default=ConnScript(close_after_hello=(1013, 'draining'))
        )
        await router.start()
        try:
            exc = await handshake_error(router.url)
        finally:
            await router.close()

        assert failure_detail(exc) == 'code=1013 reason=draining'

    def test_other_errors_use_message_or_type_name(self):
        assert failure_detail(OSError('refused')) == 'err=refused'
        assert failure_detail(TimeoutError()) == 'err=TimeoutError'

    @pytest.mark.asyncio
    async def test_body_is_truncated_to_1024_bytes(self):
        router = FakeRouter(default=ConnScript(status=503, body='x' * 4000))
        await router.start()
        try:
            exc = await handshake_error(router.url)
        finally:
            await router.close()

        assert failure_detail(exc) == 'status=503 reason=' + 'x' * 1024
