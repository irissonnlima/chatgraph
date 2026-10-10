import asyncio
from typing import Callable, Optional

from ..history.store import HistoryStore
from ..messages.log_publisher import LogPublisher
from ..messages.message_consumer import MessageConsumer
from .connection import spawn
from .consumer import StreamConsumer

_HELLO_MODE = 'dual'


class DualConsumer:
    def __init__(
        self, queue_consumer: MessageConsumer, stream_consumer: StreamConsumer
    ) -> None:
        self._queue = queue_consumer
        self._stream = stream_consumer
        self._tasks: set[asyncio.Task] = set()

    @classmethod
    def load_dotenv(cls) -> 'DualConsumer':
        return cls(
            MessageConsumer.load_dotenv(),
            StreamConsumer.load_dotenv(
                tolerant=True, mode=_HELLO_MODE, actions_via_http=True
            ),
        )

    def set_history_store(self, store: Optional[HistoryStore]) -> None:
        self._queue.set_history_store(store)
        self._stream.set_history_store(store)

    def set_log_publisher(self, publisher: Optional[LogPublisher]) -> None:
        self._queue.set_log_publisher(publisher)
        self._stream.set_log_publisher(publisher)

    async def start_consume(self, process_message: Callable) -> None:
        queue = spawn(
            self._queue.start_consume(process_message),
            'dual-queue',
            self._tasks,
        )
        stream = spawn(
            self._stream.start_consume(process_message),
            'dual-stream',
            self._tasks,
        )
        try:
            await asyncio.wait(
                {queue, stream}, return_when=asyncio.FIRST_COMPLETED
            )
        finally:
            queue.cancel()
            stream.cancel()
            await asyncio.gather(queue, stream, return_exceptions=True)
            await self.cleanup()
        for task in (stream, queue):
            if not task.cancelled() and (error := task.exception()):
                raise error

    async def cleanup(self) -> None:
        await self._queue.cleanup()
        await self._stream.cleanup()

    def reprer(self) -> None:
        self._queue.reprer()
        self._stream.reprer()
