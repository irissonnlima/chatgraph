from abc import ABC, abstractmethod
from typing import Any, Callable


class MessageConsumer(ABC):
    """
    Classe base abstrata para consumidores de mensagens no sistema do chatbot.

    Esta classe define a interface que todos os consumidores de mensagens devem implementar para serem usados no sistema do chatbot.
    """

    @abstractmethod
    def start_consume(self, process_message: Callable) -> Any:
        """
        Inicia o consumo de mensagens e processa cada mensagem usando a função fornecida.

        Args:
            process_message (Callable): Função de callback que processa cada mensagem recebida.

        Returns:
            Any: O resultado do processo de consumo de mensagens, dependendo da implementação concreta.
        """
        pass

    @abstractmethod
    def load_dotenv(self) -> 'MessageConsumer':
        """
        Carrega variáveis de ambiente para configurar o consumidor de mensagens.

        Returns:
            MessageConsumer: A instância do consumidor de mensagens configurado.
        """
        pass
