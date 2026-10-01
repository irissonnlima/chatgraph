import asyncio
import contextlib
import json
import os
import signal
from typing import Any, Callable, Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..history.store import HistoryStore
from ..logger.user_logger import UserLoggerManager
from ..messages.log_publisher import LogPublisher
from ..messages.turn import build_usercall, publish_edge_error
from ..models.userstate import ChatID
from ..types.usercall import UserCall
from .client import DRAIN_SENTINEL, StreamClient
from .connection import spawn
from .errors import InvalidDeliveryError, StreamClosedError
from .options import (
    StreamOptions,
    _Settings,
    connect_url,
    normalize_menus,
    normalize_options,
)
from .router_client import RouterStreamClient
from .runtime import _IoThread

_logger = UserLoggerManager.get_system_logger()

_SIGNALS = (signal.SIGINT, signal.SIGTERM)
_CANCEL_ATTEMPTS = 5
_CANCEL_WAIT = 0.5


class StreamConsumer:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        router_url: str,
        router_token: str,
        menus: Sequence[str],
        username: str = 'chatgraph',
        queue_size: int = 100,
        drain_timeout: float = 15.0,
        *,
        _settings: Optional[_Settings] = None,
    ) -> None:
        self._options = normalize_options(
            StreamOptions(
                router_url=router_url,
                token=router_token,
                menus=tuple(menus),
                username=username,
                queue_size=queue_size,
                drain_timeout=drain_timeout,
            )
        )
        self._settings = _settings
        self._history_store: Optional[HistoryStore] = None
        self._log_publisher: Optional[LogPublisher] = None
        self._router_client: Optional[RouterStreamClient] = None
        self._client: Optional[StreamClient] = None
        self._runtime: Optional[_IoThread] = None
        self._tasks: set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self._shutdown_requested = False
        self._signal_loop: Optional[asyncio.AbstractEventLoop] = None
        self._signals_installed: list[signal.Signals] = []
        self._in_turn = False

    @classmethod
    def load_dotenv(
        cls,
        menus_env: str = 'ROUTER_MENUS',
        router_env: str = 'ROUTER_URL',
        router_token_env: str = 'ROUTER_TOKEN',
        queue_env: str = 'RABBIT_QUEUE',
    ) -> 'StreamConsumer':
        router_url = os.getenv(router_env, '').strip()
        router_token = os.getenv(router_token_env, '').strip()
        menus = normalize_menus(os.getenv(menus_env, '').split(','))
        if not menus:
            menus = normalize_menus([os.getenv(queue_env, '')])

        envs_essentials = {
            router_env: router_url,
            router_token_env: router_token,
            menus_env: menus,
        }
        envs_missing = [k for k, v in envs_essentials.items() if not v]
        if envs_missing:
            raise ValueError(
                f'Corrija as variáveis de ambiente: {envs_missing}'
            )
        return cls(router_url, router_token, menus)

    def set_history_store(self, store: Optional[HistoryStore]) -> None:
        self._history_store = store

    def set_log_publisher(self, publisher: Optional[LogPublisher]) -> None:
        self._log_publisher = publisher

    def request_shutdown(self) -> None:
        if self._shutdown_requested:
            return
        self._shutdown_requested = True
        self._remove_signals()
        self._shutdown_event.set()

    def _install_signals(self, loop: asyncio.AbstractEventLoop) -> None:
        self._signal_loop = loop
        for sig in _SIGNALS:
            try:
                loop.add_signal_handler(sig, self.request_shutdown)
            except NotImplementedError:
                _logger.warning(
                    'Stream signal handlers unavailable on this platform'
                )
                return
            self._signals_installed.append(sig)

    def _remove_signals(self) -> None:
        for sig in self._signals_installed:
            self._signal_loop.remove_signal_handler(sig)
        self._signals_installed = []

    async def start_consume(self, process_message: Callable) -> None:
        main_loop = asyncio.get_running_loop()
        inbox: asyncio.Queue = asyncio.Queue()
        options = self._options
        self._install_signals(main_loop)
        self._router_client = RouterStreamClient(
            base_url=options.router_url,
            command=self._command,
            username=options.username,
            password=options.token,
        )
        self._runtime = _IoThread()
        self._runtime.start()
        overran = False
        try:
            self._client = await self._runtime.call(
                self._build_client(
                    lambda item: main_loop.call_soon_threadsafe(
                        inbox.put_nowait, item
                    )
                )
            )
            _logger.info(
                f'Router transport mode=stream menus={list(options.menus)}'
            )
            await self._connect()
            worker = spawn(
                self._worker(inbox, process_message), 'worker', self._tasks
            )
            waiter = spawn(
                self._shutdown_event.wait(), 'shutdown-wait', self._tasks
            )
            await asyncio.wait(
                {worker, waiter}, return_when=asyncio.FIRST_COMPLETED
            )
            if worker.done():
                await worker
                return
            overran = await self._drain(worker, inbox)
        finally:
            await self._shutdown(1001 if overran else 1000)

    async def _build_client(self, sink: Callable[[Any], None]) -> StreamClient:
        return StreamClient(self._options, self._convert, sink, self._settings)

    def _convert(self, frame: dict) -> UserCall:
        try:
            return build_usercall(
                frame, self._router_client, self._history_store
            )
        except json.JSONDecodeError as exc:
            raise InvalidDeliveryError('invalid_observation') from exc
        except Exception as exc:
            raise InvalidDeliveryError('invalid_payload') from exc

    async def _try_connect(self) -> Optional[Exception]:
        try:
            await self._runtime.call(self._client.connect())
        except Exception as exc:
            return exc
        return None

    async def _connect(self) -> None:
        connect = spawn(self._try_connect(), 'connect', self._tasks)
        waiter = spawn(
            self._shutdown_event.wait(), 'shutdown-wait', self._tasks
        )
        try:
            await asyncio.wait(
                {connect, waiter}, return_when=asyncio.FIRST_COMPLETED
            )
            if not connect.done():
                with contextlib.suppress(StreamClosedError):
                    await self._runtime.call(self._client.close())
                await asyncio.wait({connect})
                raise StreamClosedError('shutdown antes do welcome')
            error = connect.result()
            if error is not None:
                raise error
        except Exception as exc:
            _logger.error(
                'Message receiver connect failed '
                f'err={type(exc).__name__}: {exc}'
            )
            raise
        finally:
            waiter.cancel()

    async def _worker(
        self, inbox: asyncio.Queue, process_message: Callable
    ) -> None:
        while True:
            item = await inbox.get()
            if item is DRAIN_SENTINEL:
                return
            self._client.release_slot()
            self._in_turn = True
            try:
                await self._run_turn(item, process_message)
            finally:
                self._in_turn = False

    async def _run_turn(
        self, usercall: UserCall, process_message: Callable
    ) -> None:
        try:
            await process_message(usercall)
        except Exception as e:
            await publish_edge_error(self._log_publisher, e, usercall)
            _logger.error(f'Erro ao processar mensagem: {e}')
        finally:
            UserLoggerManager.remove_user_logger(
                usercall.user_id, usercall.company_id
            )

    async def _drain(self, worker: asyncio.Task, inbox: asyncio.Queue) -> bool:
        await self._runtime.call(self._client.begin_drain())
        done, _ = await asyncio.wait(
            {worker}, timeout=self._options.drain_timeout
        )
        if done:
            _logger.info('Message receiver drained')
            return False
        discarded = 1 if self._in_turn else 0
        while not inbox.empty():
            if inbox.get_nowait() is not DRAIN_SENTINEL:
                discarded += 1
        inbox.put_nowait(DRAIN_SENTINEL)
        _logger.error(f'Stream drain timeout discarded={discarded}')
        # O turno pode engolir o CancelledError (o SDK tem `except
        # BaseException`); a sentinela faz o worker sair quando ele voltar.
        for _ in range(_CANCEL_ATTEMPTS):
            worker.cancel()
            await asyncio.wait({worker}, timeout=_CANCEL_WAIT)
            if worker.done():
                return True
        _logger.error('Stream worker did not stop after cancel')
        return True

    async def _shutdown(self, code: int) -> None:
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.wait(list(self._tasks), timeout=1.0)
        if self._client is not None:
            with contextlib.suppress(StreamClosedError):
                await self._runtime.call(self._client.close(code, 'shutdown'))
        self._runtime.stop()
        await self.cleanup()
        self._remove_signals()
        _logger.info('Stream closed')

    async def _command(
        self, name: str, chat_id: ChatID, payload: dict, idempotent: bool
    ) -> None:
        await self._runtime.call(
            self._client.command(name, chat_id.to_dict(), payload, idempotent)
        )

    async def cleanup(self) -> None:
        if self._router_client is not None:
            await self._router_client.close()
            self._router_client = None

    def reprer(self) -> None:
        options = self._options
        console = Console()

        title_text = Text('ChatGraph', style='bold red', justify='center')
        title_panel = Panel.fit(
            title_text, title=' ', border_style='bold red', padding=(1, 4)
        )
        separator = Text(
            '🔌🔌🔌 StreamMessageConsumer 📨📨📨',
            style='cyan',
            justify='center',
        )

        table = Table(
            show_header=True,
            header_style='bold magenta',
            title='Stream Consumer',
        )
        table.add_column(
            'Atributo', justify='center', style='cyan', no_wrap=True
        )
        table.add_column('Valor', justify='center', style='magenta')

        table.add_row('Transport', 'stream')
        table.add_row('Menus', ', '.join(options.menus))
        table.add_row('Router URL', options.router_url)
        table.add_row('WebSocket URL', connect_url(options.router_url))
        table.add_row('Username', options.username)
        table.add_row('Token', '******')
        table.add_row('Queue size', str(options.queue_size))
        table.add_row('Drain timeout', f'{options.drain_timeout}s')

        console.print(title_panel, justify='center')
        console.print(separator, justify='center')
        console.print(table, justify='center')
