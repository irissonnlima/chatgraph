import os
from typing import Optional
from urllib.parse import quote

import aio_pika

from ..logger.user_logger import UserLoggerManager
from ..models.log_envelope import LogEnvelope

_logger = UserLoggerManager.get_system_logger()


class LogPublisher:
    def __init__(
        self,
        amqp_url: str,
        exchange: str = '/',
        queue_name: str = 'log_chatbot_queue',
        routing_key: str = '',
        heartbeat: int = 60,
        reconnect_interval: float = 5.0,
    ):
        self._amqp_url = amqp_url
        self._exchange = exchange
        self._queue_name = queue_name
        self._routing_key = routing_key or f'chatbot.{queue_name}'
        self._heartbeat = heartbeat
        self._reconnect_interval = reconnect_interval
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.Channel] = None

    @classmethod
    def load_dotenv(
        cls,
        user_env: str = 'RABBIT_USER',
        pass_env: str = 'RABBIT_PASS',
        uri_env: str = 'RABBIT_URI',
        queue_env: str = 'LOG_RABBIT_QUEUE',
        exchange_env: str = 'LOG_RABBIT_EXCHANGE',
        routing_key_env: str = 'LOG_RABBIT_ROUTING_KEY',
        heartbeat_env: str = 'RABBIT_HEARTBEAT',
        reconnect_interval_env: str = 'RABBIT_RECONNECT_INTERVAL',
    ) -> Optional['LogPublisher']:
        queue_name = os.getenv(queue_env)
        if not queue_name:
            return None
        username = os.getenv(user_env, '')
        password = os.getenv(pass_env, '')
        uri = os.getenv(uri_env, '')
        exchange = os.getenv(exchange_env, '/')
        routing_key = os.getenv(routing_key_env, '') or f'chatbot.{queue_name}'
        heartbeat = int(os.getenv(heartbeat_env, '60'))
        reconnect_interval = float(os.getenv(reconnect_interval_env, '5.0'))
        vhost = os.getenv('RABBIT_VHOST', '/')
        amqp_url = f'amqp://{quote(username)}:{quote(password)}@{uri}/{vhost}'
        return cls(
            amqp_url=amqp_url,
            exchange=exchange,
            queue_name=queue_name,
            routing_key=routing_key,
            heartbeat=heartbeat,
            reconnect_interval=reconnect_interval,
        )

    async def _ensure_connection(self) -> None:
        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(
                self._amqp_url,
                heartbeat=self._heartbeat,
            )
            self._channel = await self._connection.channel()

    async def _ensure_queue(self) -> None:
        try:
            await self._channel.declare_queue(self._queue_name, passive=True)
        except Exception:
            queue = await self._channel.declare_queue(
                self._queue_name,
                durable=True,
                auto_delete=False,
                exclusive=False,
            )
            exchange_obj = await self._channel.get_exchange(self._exchange)
            await queue.bind(
                exchange=exchange_obj,
                routing_key=self._routing_key,
            )

    async def publish_error(self, envelope: LogEnvelope) -> None:
        try:
            await self._ensure_connection()
            await self._ensure_queue()
            exchange = await self._channel.get_exchange(self._exchange)
            await exchange.publish(
                aio_pika.Message(
                    body=envelope.to_json().encode(),
                    content_type='text/plain',
                    headers={
                        'type_message': envelope.event_type,
                        'error': envelope.error,
                    },
                ),
                routing_key=self._routing_key,
            )
        except Exception as e:
            _logger.warning(f'Falha ao publicar log_error: {e}')

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        self._connection = None
        self._channel = None

    async def __aenter__(self) -> 'LogPublisher':
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()
