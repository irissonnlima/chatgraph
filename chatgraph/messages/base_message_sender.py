from abc import ABC, abstractmethod

class MessageSender(ABC):
    
    @abstractmethod
    def load_dotenv(self) -> 'MessageSender':
        """
        Carrega variáveis de ambiente para configurar o disparador de mensagens.
        
        Returns:
            MessageSender: A instância do disparador de mensagens configurado.
        """
        pass
    
    @abstractmethod
    def send_message(self) -> None:
        """
        Envia uma mensagem para o destino especificado.
        
        Args:
            message (str): A mensagem a ser enviada.
        """
        pass