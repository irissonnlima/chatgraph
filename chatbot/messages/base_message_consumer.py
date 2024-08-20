from abc import ABC, abstractmethod
from typing import Any, Callable


class MessageConsumer(ABC):
    @abstractmethod
    def start_consume(self, process_message: Callable) -> Any:
        pass
