import asyncio
import base64
import contextlib
import json
from typing import Any, Awaitable, Callable, Coroutine, Iterable

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from ..logger.user_logger import UserLoggerManager
from . import frames
from .backoff import failure_detail
from .errors import FrameTooLargeError
from .options import StreamOptions, _Settings, connect_url

_logger = UserLoggerManager.get_system_logger()

_TASK_PREFIX = 'chatgraph-stream-'
_LOGGED_FRAME_KEYS = ('delivery_id', 'cmd_id', 'name')

OnDeliver = Callable[['_Connection', dict], Awaitable[None]]


def spawn(
    coro: Coroutine[Any, Any, Any], name: str, tasks: set[asyncio.Task]
) -> asyncio.Task:
    """
    Cria uma task nomeada, referenciada em `tasks` até terminar, que loga
    a exceção em vez de deixá-la sumir junto com a task.
    """
    task = asyncio.get_running_loop().create_task(
        coro, name=f'{_TASK_PREFIX}{name}'
    )
    tasks.add(task)
    task.add_done_callback(lambda done: _on_task_done(done, tasks))
    return task


def _on_task_done(task: asyncio.Task, tasks: set[asyncio.Task]) -> None:
    tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        _logger.error(
            f'Stream task crashed name={task.get_name()} err={exc!r}'
        )


async def wait_first(
    events: Iterable[asyncio.Event], tasks: set[asyncio.Task]
) -> None:
    waiters = [spawn(event.wait(), 'wait', tasks) for event in events]
    try:
        await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for waiter in waiters:
            waiter.cancel()


class _Connection:
    def __init__(
        self,
        options: StreamOptions,
        settings: _Settings,
        on_deliver: OnDeliver,
        tasks: set[asyncio.Task],
    ) -> None:
        self.id = ''
        self.pod = ''
        self.heartbeat = settings.default_heartbeat_s * settings.heartbeat_unit
        self.last_recv = asyncio.get_running_loop().time()
        self.closed = asyncio.Event()
        self.goaway = asyncio.Event()
        self.goaway_reason = ''
        self._options = options
        self._settings = settings
        self._on_deliver = on_deliver
        self._tasks = tasks
        self._ws: ClientConnection | None = None
        self._write_lock = asyncio.Lock()
        self._ended = False
        self._pending: dict[str, asyncio.Future] = {}
        self._idle = asyncio.Event()
        self._idle.set()

    async def dial(self) -> None:
        options = self._options
        settings = self._settings
        credentials = f'{options.username}:{options.token}'.encode()
        authorization = base64.b64encode(credentials).decode('ascii')
        self._ws = await connect(
            connect_url(options.router_url),
            additional_headers=[('Authorization', f'Basic {authorization}')],
            open_timeout=settings.dial_timeout,
            ping_interval=None,
            max_size=settings.max_read_bytes,
            compression=None,
            close_timeout=settings.close_timeout,
            user_agent_header='chatgraph-python',
        )
        ready = False
        try:
            async with asyncio.timeout(settings.welcome_timeout):
                hello = frames.hello(list(options.menus), options.queue_size)
                await self._ws.send(frames.encode(hello))
                await self._await_welcome()
            ready = True
        finally:
            if not ready:
                self._abort()
                await self._ws.wait_closed()

    def start(self) -> None:
        spawn(self._read_loop(), 'read', self._tasks)
        spawn(self._ping_loop(), 'ping', self._tasks)
        spawn(self._death_loop(), 'death', self._tasks)

    async def write(self, frame: dict, timeout: float) -> None:
        data = frames.encode(frame)
        size = len(data.encode('utf-8'))
        if size > self._settings.max_frame_bytes:
            raise FrameTooLargeError(
                f'frame de {size} bytes acima de '
                f'{self._settings.max_frame_bytes}'
            )
        try:
            async with asyncio.timeout(timeout):
                async with self._write_lock:
                    await self._ws.send(data)
        except Exception as exc:
            self._die(f'write failed: {str(exc) or type(exc).__name__}')
            raise
        details = ''.join(
            f' {key}={frame[key]}'
            for key in _LOGGED_FRAME_KEYS
            if key in frame
        )
        _logger.debug(
            f'Stream frame sent conn_id={self.id} type={frame["type"]}'
            f'{details}'
        )

    async def close(self, code: int, reason: str) -> None:
        if self._ended:
            return
        self._ended = True
        try:
            if self._ws is not None:
                await self._ws.close(code, reason)
        finally:
            self.closed.set()

    def resolve(self, frame: dict) -> None:
        cmd_id = frame.get('cmd_id')
        fut = self._pending.get(cmd_id)
        if fut is not None and not fut.done():
            fut.set_result(frame)
            return
        _logger.debug(
            f'Stream late command_result conn_id={self.id} cmd_id={cmd_id}'
        )

    def pending_count(self) -> int:
        return len(self._pending)

    async def wait_idle(self) -> None:
        await self._idle.wait()

    def _abort(self) -> None:
        if self._ws is not None:
            self._ws.transport.abort()

    def _die(self, reason: str) -> None:
        if self._ended:
            return
        self._ended = True
        _logger.warning(
            f'Stream connection lost conn_id={self.id} reason={reason}'
        )
        self._abort()
        self.closed.set()

    async def _sleep(self, delay: float) -> bool:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self.closed.wait(), delay)
        return self.closed.is_set()

    def _parse(self, raw: str | bytes) -> dict | None:
        self.last_recv = asyncio.get_running_loop().time()
        try:
            frame = json.loads(raw)
        except ValueError:
            frame = None
        if not isinstance(frame, dict):
            _logger.warning(
                f'Stream invalid frame received conn_id={self.id} '
                f'size={len(raw)}'
            )
            return None
        _logger.debug(
            f'Stream frame received conn_id={self.id} type={frame.get("type")}'
        )
        return frame

    async def _await_welcome(self) -> None:
        while True:
            frame = self._parse(await self._ws.recv())
            if frame is None:
                continue
            if frame.get('type') != frames.WELCOME:
                await self._dispatch(frame)
                continue
            heartbeat_s = frame.get('heartbeat_s') or 0
            if heartbeat_s <= 0:
                heartbeat_s = self._settings.default_heartbeat_s
            self.heartbeat = heartbeat_s * self._settings.heartbeat_unit
            self.id = frame.get('conn_id', '')
            self.pod = frame.get('pod', '')
            version = frame.get('version')
            if version != frames.PROTOCOL_VERSION:
                _logger.warning(
                    f'Stream welcome version mismatch conn_id={self.id} '
                    f'version={version}'
                )
            return

    async def _dispatch(self, frame: dict) -> None:
        frame_type = frame.get('type')
        if frame_type == frames.DELIVER:
            await self._on_deliver(self, frame)
        elif frame_type == frames.COMMAND_RESULT:
            self.resolve(frame)
        elif frame_type == frames.GOAWAY:
            self.goaway_reason = str(frame.get('reason') or '')
            self.goaway.set()
        elif frame_type == frames.ERROR:
            _logger.warning(
                f'Stream error frame received conn_id={self.id} '
                f'error={frame.get("error")}'
            )
        elif frame_type != frames.PONG:
            _logger.debug(
                f'Stream unhandled frame type conn_id={self.id} '
                f'type={frame_type}'
            )

    async def _read_loop(self) -> None:
        try:
            while True:
                frame = self._parse(await self._ws.recv())
                if frame is not None:
                    await self._dispatch(frame)
        except ConnectionClosed as exc:
            self._die(f'closed {failure_detail(exc)}')
        except Exception as exc:
            self._die(f'read loop failed: {type(exc).__name__}')
            raise
        await self._ws.wait_closed()

    async def _ping_loop(self) -> None:
        while not await self._sleep(self.heartbeat):
            try:
                await self.write(frames.ping(), self.heartbeat)
            except Exception:
                return

    async def _death_loop(self) -> None:
        limit = self._settings.dead_factor * self.heartbeat
        while not await self._sleep(self.heartbeat):
            idle = asyncio.get_running_loop().time() - self.last_recv
            if idle > limit:
                self._die('no frame within 3x heartbeat_s')
                return
