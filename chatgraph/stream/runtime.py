import asyncio
import concurrent.futures
import threading
from typing import Any, Coroutine

from ..logger.user_logger import UserLoggerManager
from .errors import StreamClosedError

_logger = UserLoggerManager.get_system_logger()

THREAD_NAME = 'chatgraph-stream-io'


def _log_crash(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    _logger.error(
        f'Stream task crashed message={context.get("message")} '
        f'err={context.get("exception")!r}'
    )


class _IoThread:
    """
    Thread com event loop própria onde roda todo o I/O do stream.

    Um handler async que bloqueia a loop principal (time.sleep) não pode
    atrasar o ack nem o ping, então o WebSocket vive aqui. `call` é o
    único ponto de travessia entre as duas loops.
    """

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stopped = False

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    def start(self) -> None:
        loop = asyncio.new_event_loop()
        loop.set_exception_handler(_log_crash)
        ready = threading.Event()

        def run() -> None:
            asyncio.set_event_loop(loop)
            loop.call_soon(ready.set)
            loop.run_forever()

        self._loop = loop
        self._thread = threading.Thread(
            target=run, name=THREAD_NAME, daemon=True
        )
        self._thread.start()
        ready.wait()

    def submit(self, coro: Coroutine) -> concurrent.futures.Future:
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    async def call(self, coro: Coroutine) -> Any:
        if self._stopped or self._loop is None or not self._loop.is_running():
            coro.close()
            raise StreamClosedError('runtime do stream parado')
        future = self.submit(coro)
        try:
            return await asyncio.wrap_future(future)
        except asyncio.CancelledError:
            # Cancelado por stop() e não pelo chamador: vira erro tipado.
            if future.cancelled() and (
                asyncio.current_task().cancelling() == 0
            ):
                raise StreamClosedError('runtime do stream parado') from None
            raise

    def stop(self, timeout: float = 5.0) -> None:
        if self._stopped:
            return
        self._stopped = True
        if self._loop is None:
            return
        loop = self._loop

        async def shutdown() -> None:
            current = asyncio.current_task()
            pending = [t for t in asyncio.all_tasks() if t is not current]
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            loop.stop()

        keep: list[asyncio.Task] = []
        loop.call_soon_threadsafe(
            lambda: keep.append(
                loop.create_task(shutdown(), name='chatgraph-stream-shutdown')
            )
        )
        self._thread.join(timeout)
        if self._thread.is_alive():
            _logger.error('Stream io thread did not stop in time')
            return
        loop.close()
