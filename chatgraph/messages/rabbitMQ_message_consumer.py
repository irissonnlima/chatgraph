import json
from logging import debug, info
import os
import pika
from typing import Callable
from ..auth.credentials import Credential
from ..types.message_types import Message
from .base_message_consumer import MessageConsumer


class RabbitMessageConsumer(MessageConsumer):
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
    ) -> 'RabbitMessageConsumer':
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

        if not username or not password or not url or not queue:
            raise ValueError('Corrija as variáveis de ambiente!')

        return cls(
            credential=Credential(username=username, password=password),
            amqp_url=url,
            queue_consume=queue,
            prefetch_count=int(prefetch),
            virtual_host=vhost,
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

            info('[x] Aguardando solicitações RPC')
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
        response = process_message(pure_message)

        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            properties=pika.BasicProperties(
                correlation_id=props.correlation_id
            ),
            body=str(response),
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def __transform_message(self, message: dict) -> Message:
        """
        Transforma o dicionário JSON recebido em uma instância de Message.

        Args:
            message (dict): Dicionário contendo os dados da mensagem.

        Returns:
            Message: Uma instância da classe Message com os dados extraídos do dicionário.
        """
        return Message(
            type=message.get('type', ''),
            text=message.get('text', ''),
            customer_id=message.get('customer_id', ''),
            channel=message.get('channel', ''),
            customer_phone=message.get('customer_phone', ''),
            company_phone=message.get('company_phone', ''),
            status=message.get('status'),
        )
