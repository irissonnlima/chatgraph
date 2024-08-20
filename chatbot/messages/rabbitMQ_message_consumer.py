import json
from logging import debug, info

import pika

from ..auth.credentials import Credential
from ..types.message_types import Message
from .base_message_consumer import MessageConsumer


class RabbitMessageConsumer(MessageConsumer):
    def __init__(
        self,
        amqp_url: str,
        queue_consume: str,
        credentials: Credential,
        prefetch_count: int = 1,
        virtual_host: str = '/',
    ) -> None:
        self.__virtual_host = virtual_host
        self.__prefetch_count = prefetch_count
        self.__queue_consume = queue_consume
        self.__amqp_url = amqp_url
        self.__credentials = pika.PlainCredentials(
            credentials.username, credentials.password
        )

    def start_consume(self, process_message: callable):
        try:  # Verificar se recursão não vai estourar
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

    def on_request(self, ch, method, props, body, process_message):
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
        return Message(
            type=message.get('type', ''),
            text=message.get('text', ''),
            customer_id=message.get('customer_id', ''),
            channel=message.get('channel', ''),
            customer_phone=message.get('customer_phone', ''),
            company_phone=message.get('company_phone', ''),
            status=message.get('status'),
        )
