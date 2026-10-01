"""
Router WebSocket falso, em processo, para os testes do modo stream.

Cada tentativa de conexão segue um roteiro (`ConnScript`); a n-ésima
tentativa usa `scripts[n]` e, sem roteiro, o `default`.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, Awaitable, Callable

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from chatgraph.stream.client import StreamClient
from chatgraph.stream.options import StreamOptions, _Settings


@dataclass
class ConnScript:
    status: int | None = None
    body: str = ''
    close_after_hello: tuple[int, str] | None = None
    welcome_delay: float = 0.0
    deliver_before_welcome: dict | None = None
    on_hello: Callable[[], Awaitable[None]] | None = None
    heartbeat_s: int = 5
    answer_ping: bool = True
    silent: bool = False
    abort_after_welcome: bool = False


@dataclass
class FakeConn:
    index: int
    ws: ServerConnection
    script: ConnScript
    frames: list[tuple[float, dict]] = field(default_factory=list)
    close_code: int | None = None
    close_reason: str | None = None
    welcome_at: float | None = None
    closed_at: float | None = None
    closed: asyncio.Event = field(default_factory=asyncio.Event)

    def of_type(self, frame_type: str) -> list[dict]:
        return [f for _, f in self.frames if f.get('type') == frame_type]

    async def send(self, frame: dict) -> None:
        await self.ws.send(json.dumps(frame))

    def abort(self) -> None:
        self.ws.transport.abort()


@dataclass
class Attempt:
    index: int
    script: ConnScript
    at: float
    authorization: str | None
    conn: FakeConn | None = None


class FakeRouter:
    def __init__(
        self,
        scripts: list[ConnScript] | None = None,
        default: ConnScript | None = None,
    ) -> None:
        self.scripts = scripts or []
        self.default = default or ConnScript()
        self.attempts: list[Attempt] = []
        self.conns: list[FakeConn] = []
        self._by_ws: dict[ServerConnection, Attempt] = {}
        self._server: Server | None = None
        self.url = ''

    async def start(self) -> None:
        self._server = await serve(
            self._handle,
            '127.0.0.1',
            0,
            process_request=self._process_request,
            ping_interval=None,
            max_size=None,
            compression=None,
        )
        port = self._server.sockets[0].getsockname()[1]
        self.url = f'http://127.0.0.1:{port}'

    async def close(self) -> None:
        self._server.close()
        await self._server.wait_closed()

    def _process_request(self, ws: ServerConnection, request: Any) -> Any:
        index = len(self.attempts)
        script = (
            self.scripts[index] if index < len(self.scripts) else self.default
        )
        attempt = Attempt(
            index=index,
            script=script,
            at=asyncio.get_running_loop().time(),
            authorization=request.headers.get('Authorization'),
        )
        self.attempts.append(attempt)
        self._by_ws[ws] = attempt
        if script.status is not None:
            return ws.respond(HTTPStatus(script.status), script.body)
        return None

    async def _handle(self, ws: ServerConnection) -> None:
        attempt = self._by_ws.pop(ws)
        conn = FakeConn(attempt.index, ws, attempt.script)
        attempt.conn = conn
        self.conns.append(conn)
        try:
            await self._run(conn)
        except ConnectionClosed:
            pass
        finally:
            close_rcvd = ws.protocol.close_rcvd
            if close_rcvd is not None:
                conn.close_code = close_rcvd.code
                conn.close_reason = close_rcvd.reason
            conn.closed_at = asyncio.get_running_loop().time()
            conn.closed.set()

    @staticmethod
    def _record(conn: FakeConn, raw: str | bytes) -> dict:
        frame = json.loads(raw)
        conn.frames.append((asyncio.get_running_loop().time(), frame))
        return frame

    async def _run(self, conn: FakeConn) -> None:
        script = conn.script
        self._record(conn, await conn.ws.recv())
        if script.close_after_hello is not None:
            code, reason = script.close_after_hello
            await conn.ws.close(code, reason)
            return
        if script.on_hello is not None:
            await script.on_hello()
        if script.deliver_before_welcome is not None:
            await conn.send(script.deliver_before_welcome)
        if script.welcome_delay:
            await asyncio.sleep(script.welcome_delay)
        conn.welcome_at = asyncio.get_running_loop().time()
        await conn.send({
            'type': 'welcome',
            'conn_id': f'conn-{conn.index}',
            'pod': 'router-a',
            'heartbeat_s': script.heartbeat_s,
            'version': '1.0',
        })
        if script.abort_after_welcome:
            conn.abort()
            return
        if script.silent:
            await conn.ws.wait_closed()
            return
        async for raw in conn.ws:
            frame = self._record(conn, raw)
            if frame.get('type') == 'ping' and script.answer_ping:
                await conn.send({'type': 'pong'})


def make_deliver(
    delivery_id: str,
    msg_id: str,
    menu: str = 'rh',
    user_id: str = 'user-1',
    text: str = 'oi',
    **extra: Any,
) -> dict:
    frame = {
        'type': 'deliver',
        'delivery_id': delivery_id,
        'msg_id': msg_id,
        'menu': menu,
        'attempt': 1,
        'user_state': {
            'chat_id': {'user_id': user_id, 'company_id': 'company-1'},
            'platform': 'voll',
            'observation': '{"step":1}',
        },
        'message': {'text_message': {'title': '', 'detail': text}},
        'platform_state': {'voll': {'foo': 'bar'}},
    }
    frame.update(extra)
    return frame


async def eventually(
    predicate: Callable[[], Any], timeout: float = 2.0
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.005)
    raise AssertionError(f'condição não atingida em {timeout}s')


class Sink:
    def __init__(self) -> None:
        self.items: list[Any] = []

    def __call__(self, item: Any) -> None:
        self.items.append(item)


@asynccontextmanager
async def stream_client(
    router: FakeRouter,
    settings: _Settings,
    menus: tuple[str, ...] = ('rh',),
    convert: Callable[[dict], Any] | None = None,
    **options: Any,
):
    sink = Sink()
    client = StreamClient(
        StreamOptions(
            router_url=router.url, token='tok-1', menus=menus, **options
        ),
        convert or (lambda frame: frame),
        sink,
        settings,
    )
    try:
        yield client, sink
    finally:
        await client.close()
