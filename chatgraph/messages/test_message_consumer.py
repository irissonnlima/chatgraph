from typing import Any, Callable
from .base_message_consumer import MessageConsumer


class TestMessageConsumer(MessageConsumer):
    """
    Classe de consumidor de mensagens de teste para uso em testes unitários.
    """
    def __init__(self) -> None:
        super().__init__()
        
    @classmethod
    def load_dotenv(cls) -> 'TestMessageConsumer':
        return cls()
    
    def start_consume(self, process_message: Callable) -> Any:
        return super().start_consume(process_message)