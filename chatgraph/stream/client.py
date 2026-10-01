import asyncio
import contextlib
import itertools
import secrets
import threading
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Final

from websockets.exceptions import InvalidStatus

from ..logger.user_logger import UserLoggerManager
from . import frames
from .backoff import FailureClass, classify, failure_detail, full_jitter
from .connection import _Connection, spawn, wait_first
from .dedupe import LRU
from .errors import (
    CommandFailedError,
    CommandTimeoutError,
    ConnectionLostError,
    FrameTooLargeError,
    InvalidDeliveryError,
    SessionNotOwnedError,
    StreamClosedError,
    StreamRejectedError,
)
from .options import StreamOptions, _Settings, normalize_options

_logger = UserLoggerManager.get_system_logger()

DRAIN_SENTINEL: Final = object()

_REJECTIONS = {
    401: '401 unauthorized',
    403: '403 forbidden',
    404: '404 (router não está em modo stream?)',
}


@dataclass
class _ChatLock:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    refs: int = 0


def _rejection_message(exc: BaseException) -> str:
    if isinstance(exc, InvalidStatus):
        return _REJECTIONS[exc.response.status_code]
    return f'{exc.rcvd.code} {exc.rcvd.reason}'


def _has_required_fields(frame: dict) -> bool:
    user_state = frame.get('user_state')
    if not isinstance(user_state, dict):
        return False
    chat_id = user_state.get('chat_id')
    if not isinstance(chat_id, dict) or not chat_id.get('user_id'):
        return False
    msg_id = frame.get('msg_id')
    menu = frame.get('menu')
    if not isinstance(msg_id, str) or not isinstance(menu, str):
        return False
    if not msg_id or not menu:
        return False
    return isinstance(frame.get('message'), dict)


async def _send_ack(conn: _Connection, frame: dict) -> None:
    try:
        await conn.write(
            frames.ack(frame['delivery_id'], frame['msg_id']), conn.heartbeat
        )
    except Exception as exc:
        _logger.warning(
            f'Stream ack write failed conn_id={conn.id} '
            f'err={str(exc) or type(exc).__name__}'
        )


async def _send_nack(
    conn: _Connection, frame: dict, retryable: bool, error: str
) -> None:
    nack = frames.nack(
        frame['delivery_id'], frame.get('msg_id') or '', retryable, error
    )
    try:
        await conn.write(nack, conn.heartbeat)
    except Exception as exc:
        _logger.warning(
            f'Stream nack write failed conn_id={conn.id} '
            f'err={str(exc) or type(exc).__name__}'
        )


def _raise_for_result(name: str, cmd_id: str, result: dict) -> None:
    if result.get('ok') is True:
        return
    error = str(result.get('error') or '')
    if error.startswith('session_not_owned'):
        _logger.warning(
            f'Stream command session not owned name={name} '
            f'cmd_id={cmd_id} error={error}'
        )
        raise SessionNotOwnedError(error)
    _logger.error(
        f'Stream command failed name={name} cmd_id={cmd_id} error={error}'
    )
    raise CommandFailedError(f'{name}: {error}')


class StreamClient:
    def __init__(
        self,
        options: StreamOptions,
        convert: Callable[[dict], Any],
        sink: Callable[[Any], None],
        settings: _Settings | None = None,
    ) -> None:
        self._options = normalize_options(options)
        self._settings = settings or _Settings()
        self._convert = convert
        self._sink = sink
        self._menus = frozenset(self._options.menus)
        self._dedupe = LRU(self._settings.dedupe_capacity)
        self._accept_lock = asyncio.Lock()
        self._draining = False
        self._reserve_lock = threading.Lock()
        self._reserved = 0
        self._tasks: set[asyncio.Task] = set()
        self._current: _Connection | None = None
        self._retired: set[_Connection] = set()
        self._conn_ready = asyncio.Event()
        self._connected_at = 0.0
        self._boot: asyncio.Future = asyncio.get_running_loop().create_future()
        self._supervisor: asyncio.Task | None = None
        self._stopped = asyncio.Event()
        self._closed = False
        self._cmd_prefix = secrets.token_hex(8)
        self._cmd_seq = itertools.count(1)
        self._chat_locks: dict[str, _ChatLock] = {}

    async def connect(self) -> None:
        if self._closed:
            raise StreamClosedError('client fechado')
        if self._supervisor is None:
            self._supervisor = spawn(
                self._supervise(), 'supervisor', self._tasks
            )
        await asyncio.shield(self._boot)

    async def command(
        self, name: str, chat_id: dict, payload: dict, idempotent: bool
    ) -> None:
        if self._closed:
            raise StreamClosedError('client fechado')
        cmd_id = f'{self._cmd_prefix}-{next(self._cmd_seq)}'
        frame = frames.command(cmd_id, name, chat_id, payload)
        size = len(frames.encode(frame).encode('utf-8'))
        if size > self._settings.max_frame_bytes:
            raise FrameTooLargeError(name)
        async with self._chat_lock(chat_id):
            await self._execute(name, cmd_id, frame, idempotent)

    @contextlib.asynccontextmanager
    async def _chat_lock(self, chat_id: dict) -> AsyncIterator[None]:
        key = f'{chat_id["user_id"]}|{chat_id["company_id"]}'
        entry = self._chat_locks.setdefault(key, _ChatLock())
        entry.refs += 1
        try:
            async with entry.lock:
                yield
        finally:
            entry.refs -= 1
            if entry.refs == 0:
                del self._chat_locks[key]

    async def _execute(
        self, name: str, cmd_id: str, frame: dict, idempotent: bool
    ) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._settings.command_timeout
        while True:
            conn = await self._wait_conn(name, cmd_id, deadline)
            fut = conn.register(cmd_id)
            waiters = [
                spawn(event.wait(), 'wait', self._tasks)
                for event in (conn.closed, self._stopped)
            ]
            try:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise CommandTimeoutError(name)
                try:
                    await conn.write(frame, remaining)
                except Exception:
                    if loop.time() >= deadline:
                        raise CommandTimeoutError(name) from None
                    continue
                await asyncio.wait(
                    [fut, *waiters],
                    timeout=deadline - loop.time(),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if fut.done():
                    _raise_for_result(name, cmd_id, fut.result())
                    return
                if self._stopped.is_set():
                    raise StreamClosedError(name)
                if conn.closed.is_set():
                    if idempotent:
                        continue
                    raise ConnectionLostError(name)
                raise CommandTimeoutError(name)
            finally:
                for waiter in waiters:
                    waiter.cancel()
                conn.unregister(cmd_id)

    async def _wait_conn(
        self, name: str, cmd_id: str, deadline: float
    ) -> _Connection:
        loop = asyncio.get_running_loop()
        while True:
            if self._closed:
                raise StreamClosedError(name)
            conn = self._current
            if conn is not None and not conn.closed.is_set():
                return conn
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise CommandTimeoutError(f'{name} aguardando conexão')
            _logger.debug(
                f'Stream command waiting for connection name={name} '
                f'cmd_id={cmd_id}'
            )
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._conn_ready.wait(), remaining)

    async def begin_drain(self) -> None:
        async with self._accept_lock:
            if self._draining:
                return
            self._draining = True
            _logger.info('Stream draining')
            self._sink(DRAIN_SENTINEL)

    async def close(self, code: int = 1000, reason: str = 'shutdown') -> None:
        if self._closed:
            return
        self._closed = True
        self._stopped.set()
        self._conn_ready.set()
        if self._supervisor is not None:
            self._supervisor.cancel()
        self._resolve_boot(StreamClosedError('client fechado'))
        connections = [self._current, *self._retired]
        self._current = None
        for conn in connections:
            if conn is not None:
                await conn.close(code, reason)
        for task in list(self._tasks):
            task.cancel()
        await self._wait_tasks()

    def reserve_slot(self) -> bool:
        with self._reserve_lock:
            if self._reserved >= self._options.queue_size:
                return False
            self._reserved += 1
            return True

    def release_slot(self) -> None:
        with self._reserve_lock:
            if self._reserved > 0:
                self._reserved -= 1

    def pending_commands(self) -> int:
        connections = [self._current, *self._retired]
        return sum(c.pending_count() for c in connections if c is not None)

    def _resolve_boot(self, error: Exception | None = None) -> None:
        if self._boot.done():
            return
        if error is None:
            self._boot.set_result(None)
            return
        self._boot.set_exception(error)
        self._boot.exception()

    async def _wait_tasks(self) -> None:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._settings.close_timeout + 1
        while self._tasks:
            remaining = deadline - loop.time()
            if remaining <= 0:
                return
            await asyncio.wait(list(self._tasks), timeout=remaining)

    async def _sleep(self, delay: float) -> bool:
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._stopped.wait(), delay)
        return self._stopped.is_set()

    def _promote(self, conn: _Connection) -> None:
        self._current = conn
        self._connected_at = asyncio.get_running_loop().time()
        ready, self._conn_ready = self._conn_ready, asyncio.Event()
        ready.set()

    def _demote(self, conn: _Connection) -> None:
        if self._current is conn:
            self._current = None

    async def _dial(self) -> _Connection:
        conn = _Connection(
            self._options, self._settings, self._handle_deliver, self._tasks
        )
        await conn.dial()
        conn.start()
        return conn

    async def _supervise(self) -> None:
        settings = self._settings
        attempt = 0
        try:
            while not self._stopped.is_set():
                try:
                    conn = await self._dial()
                except Exception as exc:
                    next_attempt = await self._on_dial_failure(exc, attempt)
                    if next_attempt is None:
                        return
                    attempt = next_attempt
                    continue
                self._promote(conn)
                _logger.info(
                    f'Stream connected conn_id={conn.id} pod={conn.pod} '
                    f'heartbeat={conn.heartbeat}'
                )
                self._resolve_boot()
                if await self._monitor(conn) is None:
                    return
                lived = asyncio.get_running_loop().time() - self._connected_at
                if lived > settings.backoff_cap:
                    attempt = 0
                delay = full_jitter(
                    attempt,
                    settings.backoff_base,
                    settings.backoff_cap,
                    settings.rand,
                )
                attempt += 1
                if await self._sleep(delay):
                    return
        finally:
            self._current = None
            self._resolve_boot(StreamClosedError('client fechado'))

    async def _on_dial_failure(
        self, exc: Exception, attempt: int
    ) -> int | None:
        settings = self._settings
        failure = classify(exc)
        if failure is FailureClass.CONFIG:
            if not self._boot.done():
                self._resolve_boot(
                    StreamRejectedError(_rejection_message(exc))
                )
                return None
            _logger.error(f'Stream rejected, retrying {failure_detail(exc)}')
            delay = settings.auth_retry_delay
        else:
            cap = settings.backoff_cap
            if failure is FailureClass.SHORT:
                cap = settings.short_backoff_cap
                _logger.info(
                    'Stream reconnect backoff class=short '
                    f'{failure_detail(exc)}'
                )
            else:
                _logger.warning(
                    'Stream reconnect backoff class=network '
                    f'{failure_detail(exc)}'
                )
            delay = full_jitter(
                attempt, settings.backoff_base, cap, settings.rand
            )
            attempt += 1
        if await self._sleep(delay):
            return None
        return attempt

    async def _monitor(self, conn: _Connection) -> _Connection | None:
        while True:
            await wait_first(
                [conn.closed, conn.goaway, self._stopped], self._tasks
            )
            if self._stopped.is_set():
                return None
            if conn.closed.is_set():
                self._demote(conn)
                return conn
            _logger.info(
                f'Stream goaway received conn_id={conn.id} '
                f'reason={conn.goaway_reason}'
            )
            replacement = await self._handle_goaway(conn)
            if replacement is None:
                return None
            conn = replacement

    async def _handle_goaway(self, old: _Connection) -> _Connection | None:
        watcher = spawn(self._demote_when_closed(old), 'demote', self._tasks)
        attempt = 0
        try:
            while not self._stopped.is_set():
                try:
                    conn = await self._dial()
                except Exception as exc:
                    next_attempt = await self._on_dial_failure(exc, attempt)
                    if next_attempt is None:
                        return None
                    attempt = next_attempt
                    continue
                self._promote(conn)
                _logger.info(
                    f'Stream connection replaced old_conn_id={old.id} '
                    f'conn_id={conn.id} pod={conn.pod}'
                )
                self._retire(old)
                return conn
            return None
        finally:
            watcher.cancel()

    async def _demote_when_closed(self, conn: _Connection) -> None:
        await conn.closed.wait()
        self._demote(conn)

    def _retire(self, old: _Connection) -> None:
        self._retired.add(old)
        spawn(self._retire_when_idle(old), 'retire', self._tasks)

    async def _retire_when_idle(self, old: _Connection) -> None:
        try:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(
                    old.wait_idle(), self._settings.command_timeout
                )
            await old.close(1000, 'goaway: replaced')
        finally:
            self._retired.discard(old)

    async def _handle_deliver(self, conn: _Connection, frame: dict) -> None:
        delivery_id = frame.get('delivery_id')
        msg_id = frame.get('msg_id')
        menu = frame.get('menu')
        if not delivery_id:
            _logger.warning(
                f'Stream deliver missing delivery_id msg_id={msg_id} '
                f'menu={menu}'
            )
            return

        reason = self._validate(frame)
        if reason is not None:
            await _send_nack(conn, frame, False, reason)
            return

        try:
            item = self._convert(frame)
        except InvalidDeliveryError as exc:
            if exc.reason == 'invalid_observation':
                _logger.warning(
                    'Stream deliver observation invalid '
                    f'menu={menu} msg_id={msg_id}'
                )
            await _send_nack(conn, frame, False, exc.reason)
            return
        except Exception:
            await _send_nack(conn, frame, False, 'invalid_payload')
            return

        key = f'{msg_id}:{menu}'
        async with self._accept_lock:
            if self._dedupe.seen(key):
                await _send_ack(conn, frame)
            elif self._draining:
                await _send_nack(conn, frame, True, 'draining')
            elif not self.reserve_slot():
                _logger.warning(
                    f'Stream delivery queue full menu={menu} conn_id={conn.id}'
                )
                await _send_nack(conn, frame, True, 'queue_full')
            else:
                self._dedupe.add(key)
                await _send_ack(conn, frame)
                self._sink(item)

    def _validate(self, frame: dict) -> str | None:
        if not _has_required_fields(frame):
            return 'invalid_payload'
        if frame['menu'] not in self._menus:
            return 'menu_not_served'
        return None
