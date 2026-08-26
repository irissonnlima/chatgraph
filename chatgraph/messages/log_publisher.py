import os
from typing import Optional
from urllib.parse import quote

import aio_pika

from ..logger.user_logger import UserLoggerManager
from ..models.log_envelope import LogEnvelope

_logger = UserLoggerManager.get_system_logger()

# '/' é sintaxe de vhost, nunca nome de exchange: um get_exchange('/')
# devolve NOT_FOUND e o broker fecha o canal. Nome vazio é a exchange
# default do AMQP, que existe em todo vhost.
_DEFAULT_EXCHANGE = ''

# Uma retentativa é suficiente: a primeira tentativa é quem descobre que o
# canal morreu, a segunda já roda em canal novo.
_PUBLISH_ATTEMPTS = 2


def _resolve_exchange(explicit: Optional[str], vhost: str) -> str:
    """Resolve o nome da exchange de logs.

    Convenção da infra: a exchange tem o mesmo nome do vhost. O vhost '/'
    não tem exchange homônima, então cai na exchange default.
    """
    if explicit:
        return _DEFAULT_EXCHANGE if explicit == '/' else explicit
    if vhost and vhost != '/':
        return vhost
    return _DEFAULT_EXCHANGE


class LogPublisher:
    def __init__(
        self,
        amqp_url: str,
        exchange: str = _DEFAULT_EXCHANGE,
        queue_name: str = 'log_chatbot_queue',
        routing_key: str = '',
        heartbeat: int = 60,
        reconnect_interval: float = 5.0,
    ):
        self._amqp_url = amqp_url
        self._exchange = _DEFAULT_EXCHANGE if exchange == '/' else exchange
        self._queue_name = queue_name
        # Na exchange default o RabbitMQ roteia pelo nome da fila: uma
        # routing key 'chatbot.<fila>' sairia unroutable e a mensagem seria
        # descartada em silêncio (não publicamos com mandatory).
        self._routing_key = routing_key or (
            f'chatbot.{queue_name}' if self._exchange else queue_name
        )
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
        vhost_env: str = 'RABBIT_VHOST',
    ) -> Optional['LogPublisher']:
        queue_name = os.getenv(queue_env)
        if not queue_name:
            return None
        username = os.getenv(user_env, '')
        password = os.getenv(pass_env, '')
        uri = os.getenv(uri_env, '')
        vhost = os.getenv(vhost_env, '/')
        exchange = _resolve_exchange(os.getenv(exchange_env), vhost)
        routing_key = os.getenv(routing_key_env, '')
        heartbeat = int(os.getenv(heartbeat_env, '60'))
        reconnect_interval = float(os.getenv(reconnect_interval_env, '5.0'))
        vhost_path = quote(vhost, safe='')
        amqp_url = (
            f'amqp://{quote(username)}:{quote(password)}@{uri}/{vhost_path}'
        )
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
            self._channel = None
        # Erro de canal (um declare passivo em fila ou exchange inexistente,
        # por exemplo) fecha apenas o canal e mantém a conexão viva. Sem
        # recriar o canal aqui, a publicação seguinte reusaria o canal morto
        # e estouraria em 'Channel closed by RPC timeout'.
        if self._channel is None or self._channel.is_closed:
            self._channel = await self._connection.channel()

    async def _discard_channel(self) -> None:
        """Descarta o canal atual; o próximo _ensure_connection recria."""
        channel, self._channel = self._channel, None
        if channel is None or channel.is_closed:
            return
        try:
            await channel.close()
        except Exception:
            # Fechar canal já morto é irrelevante: o objetivo é só soltar
            # a referência para não reusá-lo.
            pass

    async def _get_exchange(self) -> aio_pika.abc.AbstractExchange:
        if not self._exchange:
            return self._channel.default_exchange
        return await self._channel.get_exchange(self._exchange)

    async def _ensure_queue(self) -> None:
        try:
            await self._channel.declare_queue(self._queue_name, passive=True)
            return
        except Exception:
            # O declare passivo que falha é erro de canal: o broker fecha o
            # canal, então o declare ativo abaixo precisa de um canal novo.
            await self._discard_channel()
            await self._ensure_connection()

        queue = await self._channel.declare_queue(
            self._queue_name,
            durable=True,
            auto_delete=False,
            exclusive=False,
        )
        if not self._exchange:
            # Bind na exchange default é recusado pelo broker
            # (ACCESS_REFUSED): nela o roteamento é pelo nome da fila.
            return
        exchange_obj = await self._get_exchange()
        await queue.bind(
            exchange=exchange_obj,
            routing_key=self._routing_key,
        )

    async def publish_error(self, envelope: LogEnvelope) -> None:
        message = aio_pika.Message(
            body=envelope.to_json().encode(),
            content_type='text/plain',
            headers={
                'type_message': envelope.event_type,
                'error': envelope.error,
            },
        )
        # Um erro de canal derruba o canal sem derrubar a conexão, e é a
        # primeira tentativa que descobre isso.
        for attempt in range(1, _PUBLISH_ATTEMPTS + 1):
            try:
                await self._ensure_connection()
                await self._ensure_queue()
                exchange = await self._get_exchange()
                await exchange.publish(
                    message,
                    routing_key=self._routing_key,
                )
                return
            except Exception as e:
                await self._discard_channel()
                if attempt == _PUBLISH_ATTEMPTS:
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
