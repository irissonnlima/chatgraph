from .base_message_sender import MessageSender
from ..auth.credentials import Credential
import pika
import os

class RabbitMessageSender(MessageSender):
    def __init__(
        self,
        credential: Credential,
        amqp_url: str,
        send_queue: str,
        virtual_host: str = '/',
    ) -> None:
        """
        Inicializa o consumidor de mensagens RabbitMQ com as configurações fornecidas.

        Args:
            credential (Credential): Credenciais de autenticação para o RabbitMQ.
            amqp_url (str): A URL de conexão AMQP do RabbitMQ.
            queue_consume (str): O nome da fila de consumo.
            prefetch_count (int, opcional): O número de mensagens pré-carregadas. Padrão é 1.
            virtual_host (str, opcional): O host virtual do RabbitMQ. Padrão é '/'.
        """
        self.__virtual_host = virtual_host
        self.__send_queue = send_queue
        self.__amqp_url = amqp_url
        self.__credentials = pika.PlainCredentials(
            credential.username, credential.password
        )
    
    @classmethod
    def load_dotenv(
        cls,
        user_env: str = 'RABBIT_USER',
        pass_env: str = 'RABBIT_PASS',
        uri_env: str = 'RABBIT_URI',
        queue_env: str = 'RABBIT_QUEUE',
        prefetch_env: str = 'RABBIT_PREFETCH',
        vhost_env: str = 'RABBIT_VHOST',
    ) -> 'RabbitMessageSender':
        """
        Carrega variáveis de ambiente para configurar o disparador de mensagens.
        Args:
            user_env (str): Nome da variável de ambiente para o usuário do RabbitMQ. Padrão é 'RABBIT_USER'.
            pass_env (str): Nome da variável de ambiente para a senha do RabbitMQ. Padrão é 'RABBIT_PASS'.
            uri_env (str): Nome da variável de ambiente para a URL do RabbitMQ. Padrão é 'RABBIT_URI'.
            queue_env (str): Nome da variável de ambiente para a fila de consumo do RabbitMQ. Padrão é 'RABBIT_QUEUE'.
            prefetch_env (str): Nome da variável de ambiente para o prefetch count. Padrão é 'RABBIT_PREFETCH'.
            vhost_env (str): Nome da variável de ambiente para o host virtual do RabbitMQ. Padrão é 'RABBIT_VHOST'.
        Raises:
            ValueError: Se as variáveis de ambiente não forem configuradas corret
        Returns:
            RabbitMessageSender: A instância do disparador de mensagens configurado.
        """
        username = os.getenv(user_env)
        password = os.getenv(pass_env)
        url = os.getenv(uri_env)
        queue = os.getenv(queue_env)
        vhost = os.getenv(vhost_env, '/')

        if not username or not password or not url or not queue:
            raise ValueError('Corrija as variáveis de ambiente!')

        return cls(
            credential=Credential(username=username, password=password),
            amqp_url=url,
            send_queue=queue,
            virtual_host=vhost,
        )
    
    
    def send_message(self) -> None:
        """
        Envia uma mensagem para o destino especificado.
        
        Args:
            message (str): A mensagem a ser enviada.
        """
        pass