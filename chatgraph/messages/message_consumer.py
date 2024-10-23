import json
from logging import debug, info
import os
import pika
from typing import Callable
from ..auth.credentials import Credential
from ..types.request_types import UserCall, UserState
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

class MessageConsumer:
    """
    Implementação de MessageConsumer para consumir mensagens de uma fila RabbitMQ.

    Atributos:
        __virtual_host (str): O host virtual usado para a conexão RabbitMQ.
        __prefetch_count (int): O número de mensagens pré-carregadas que o consumidor pode processar.
        __queue_consume (str): O nome da fila de consumo.
        __amqp_url (str): A URL de conexão AMQP do RabbitMQ.
        __credentials (pika.PlainCredentials): Credenciais do RabbitMQ para autenticação.
    """

    def __init__(
        self,
        credential: Credential,
        amqp_url: str,
        grpc_uri: str,
        queue_consume: str,
        prefetch_count: int = 1,
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
        self.__prefetch_count = prefetch_count
        self.__queue_consume = queue_consume
        self.__amqp_url = amqp_url
        self.__grpc_uri = grpc_uri
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
        grpc_uri: str = 'GRPC_URI',
    ) -> 'MessageConsumer':
        """
        Carrega as configurações do RabbitMQ a partir de variáveis de ambiente e retorna uma instância de RabbitMessageConsumer.

        Args:
            user_env (str): Nome da variável de ambiente para o usuário do RabbitMQ. Padrão é 'RABBIT_USER'.
            pass_env (str): Nome da variável de ambiente para a senha do RabbitMQ. Padrão é 'RABBIT_PASS'.
            uri_env (str): Nome da variável de ambiente para a URL do RabbitMQ. Padrão é 'RABBIT_URI'.
            queue_env (str): Nome da variável de ambiente para a fila de consumo do RabbitMQ. Padrão é 'RABBIT_QUEUE'.
            prefetch_env (str): Nome da variável de ambiente para o prefetch count. Padrão é 'RABBIT_PREFETCH'.
            vhost_env (str): Nome da variável de ambiente para o host virtual do RabbitMQ. Padrão é 'RABBIT_VHOST'.

        Raises:
            ValueError: Se qualquer uma das variáveis de ambiente necessárias não estiver definida.

        Returns:
            RabbitMessageConsumer: Uma instância configurada do RabbitMessageConsumer.
        """
        username = os.getenv(user_env)
        password = os.getenv(pass_env)
        url = os.getenv(uri_env)
        queue = os.getenv(queue_env)
        prefetch = os.getenv(prefetch_env, 1)
        vhost = os.getenv(vhost_env, '/')
        grpc = os.getenv(grpc_uri)

        if not username or not password or not url or not queue or not grpc:
            raise ValueError('Corrija as variáveis de ambiente!')

        return cls(
            credential=Credential(username=username, password=password),
            amqp_url=url,
            queue_consume=queue,
            prefetch_count=int(prefetch),
            virtual_host=vhost,
            grpc_uri=grpc,
        )

    def start_consume(self, process_message: Callable) -> None:
        """
        Inicia o consumo de mensagens da fila RabbitMQ e processa cada mensagem usando a função fornecida.

        Args:
            process_message (Callable): Função de callback que processa cada mensagem recebida.

        Raises:
            pika.exceptions.StreamLostError: Se a conexão com o RabbitMQ for perdida, tentará reconectar automaticamente.
        """
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self.__amqp_url,
                    virtual_host=self.__virtual_host,
                    credentials=self.__credentials,
                )
            )
            channel = connection.channel()

            channel.basic_qos(prefetch_count=self.__prefetch_count)
            channel.basic_consume(
                queue=self.__queue_consume,
                on_message_callback=lambda c, m, p, b: self.on_request(
                    c, m, p, b, process_message
                ),
            )

            info('[x] Server inicializado! Aguardando solicitações RPC')
            channel.start_consuming()
        except pika.exceptions.StreamLostError as e:
            debug(e)
            self.start_consume(process_message)

    def on_request(self, ch, method, props, body, process_message) -> None:
        """
        Processa uma mensagem recebida e publica a resposta de volta na fila especificada.

        Args:
            ch: Canal do RabbitMQ.
            method: Método de entrega do RabbitMQ.
            props: Propriedades da mensagem do RabbitMQ.
            body: Corpo da mensagem recebida.
            process_message (Callable): Função que processa a mensagem e retorna uma resposta.
        """
        message = body.decode()
        message_json = json.loads(message)
        pure_message = self.__transform_message(message_json)
        process_message(pure_message)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def __transform_message(self, message: dict) -> UserCall:
        """
        Transforma o dicionário JSON recebido em uma instância de Message.

        Args:
            message (dict): Dicionário contendo os dados da mensagem.

        Returns:
            Message: Uma instância da classe Message com os dados extraídos do dicionário.
        """
        
        user_state = message.get('user_state', {})
        obs = user_state.get('obs', {})
        if isinstance(obs, str):
            obs = json.loads(obs)
            
        return UserCall(
            type=message.get('type', ''),
            text=message.get('text', ''),
            user_state=UserState(
                customer_id=user_state.get('customer_id', ''),
                menu=user_state.get('menu', ''),
                route=user_state.get('route', ''),
                lst_update=user_state.get('lst_update', ''),
                obs=obs,
            ),
            channel=message.get('channel', ''),
            customer_phone=message.get('customer_phone', ''),
            company_phone=message.get('company_phone', ''),
            status=message.get('status'),
            grpc_uri=self.__grpc_uri,
        )

    def reprer(self):
        console = Console()

        # Título "ChatGraph" destacado em vermelho e negrito dentro de um painel
        title_text = Text("ChatGraph", style="bold red", justify="center")
        title_panel = Panel.fit(title_text, title=" ", border_style="bold red", padding=(1, 4))

        # Linha separadora com emojis
        separator = Text("🐇🐇🐇 RabbitMessageConsumer 📨📨📨", style="cyan", justify="center")

        # Criação da tabela com os atributos
        table = Table(show_header=True, header_style="bold magenta", title="RabbitMQ Consumer")
        table.add_column("Atributo", justify="center", style="cyan", no_wrap=True)
        table.add_column("Valor", justify="center", style="magenta")

        table.add_row("Virtual Host", self.__virtual_host)
        table.add_row("Prefetch Count", str(self.__prefetch_count))
        table.add_row("Queue Consume", self.__queue_consume)
        table.add_row("AMQP URL", self.__amqp_url)
        table.add_row("Username", self.__credentials.username)
        table.add_row("Password", "******")  # Oculta a senha

        # Imprime o título, separador e a tabela centralizada
        console.print(title_panel, justify="center")
        console.print(separator, justify="center")
        console.print(table, justify="center")
