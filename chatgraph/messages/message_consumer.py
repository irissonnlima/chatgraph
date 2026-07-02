import asyncio
import json
import os
from typing import Callable
from urllib.parse import quote

import aio_pika
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..auth.credentials import Credential
from ..logger.user_logger import UserLoggerManager
from ..models.message import Message
from ..models.platform_state import PlatformState
from ..models.userstate import UserState
from ..services.router_http_client import RouterHTTPClient
from ..types.usercall import UserCall

_logger = UserLoggerManager.get_system_logger()


class MessageConsumer:
    def __init__(
        self,
        credential: Credential,
        amqp_url: str,
        router_url: str,
        router_token: str,
        queue_consume: str,
        prefetch_count: int = 1,
        virtual_host: str = '/',
        heartbeat: int = 60,
        reconnect_interval: float = 5.0,
        x_expires: int = 86400000,
        x_message_ttl: int = 3600000,
    ) -> None:
        if heartbeat < 0:
            raise ValueError('heartbeat must be >= 0')
        if reconnect_interval < 0:
            raise ValueError('reconnect_interval must be >= 0')
        self.__virtual_host = virtual_host
        self.__prefetch_count = prefetch_count
        self.__x_expires = x_expires
        self.__x_message_ttl = x_message_ttl
        self.__queue_consume = queue_consume
        self.__amqp_url = amqp_url
        self.__router_url = router_url
        self.__router_token = router_token
        self.__credentials = credential
        self.__router_client = None
        self.__heartbeat = heartbeat
        self.__reconnect_interval = reconnect_interval

    @classmethod
    def load_dotenv(
        cls,
        user_env: str = 'RABBIT_USER',
        pass_env: str = 'RABBIT_PASS',
        uri_env: str = 'RABBIT_URI',
        queue_env: str = 'RABBIT_QUEUE',
        prefetch_env: str = 'RABBIT_PREFETCH',
        vhost_env: str = 'RABBIT_VHOST',
        router_env: str = 'ROUTER_URL',
        router_token_env: str = 'ROUTER_TOKEN',
        heartbeat_env: str = 'RABBIT_HEARTBEAT',
        reconnect_interval_env: str = 'RABBIT_RECONNECT_INTERVAL',
        x_expires_env: str = 'RABBIT_X_EXPIRES',
        x_message_ttl_env: str = 'RABBIT_X_MESSAGE_TTL',
    ) -> 'MessageConsumer':
        username = os.getenv(user_env)
        password = os.getenv(pass_env)
        url = os.getenv(uri_env)
        queue = os.getenv(queue_env)
        prefetch = os.getenv(prefetch_env, '1')
        vhost = os.getenv(vhost_env, '/')
        router_url = os.getenv(router_env)
        router_token = os.getenv(router_token_env)
        heartbeat = os.getenv(heartbeat_env, '60')
        reconnect_interval = os.getenv(reconnect_interval_env, '5.0')
        x_expires = os.getenv(x_expires_env, '86400000')
        x_message_ttl = os.getenv(x_message_ttl_env, '3600000')

        envs_essentials = {
            username: user_env,
            password: pass_env,
            url: uri_env,
            queue: queue_env,
            router_url: router_env,
            router_token: router_token_env,
        }

        if None in envs_essentials:
            envs_missing = [v for k, v in envs_essentials.items() if k is None]
            raise ValueError(
                f'Corrija as variáveis de ambiente: {envs_missing}'
            )

        return cls(
            credential=Credential(username=username, password=password),
            amqp_url=url,
            queue_consume=queue,
            prefetch_count=int(prefetch),
            virtual_host=vhost,
            router_url=router_url,
            router_token=router_token,
            heartbeat=int(heartbeat),
            reconnect_interval=float(reconnect_interval),
            x_expires=int(x_expires),
            x_message_ttl=int(x_message_ttl),
        )

    async def __initialize_router(self) -> RouterHTTPClient:
        """Inicializa o cliente HTTP apenas uma vez (singleton)."""
        if self.__router_client is None:
            self.__router_client = RouterHTTPClient(
                base_url=self.__router_url,
                username='chatgraph',
                password=self.__router_token,
            )
        return self.__router_client

    def __build_amqp_url(self) -> str:
        user = quote(self.__credentials.username)
        pwd = quote(self.__credentials.password)
        vhost = quote(self.__virtual_host, safe='')
        return f'amqp://{user}:{pwd}@{self.__amqp_url}/{vhost}'

    async def __declare_queue(self, channel) -> aio_pika.abc.AbstractQueue:
        arguments = {
            'x-dead-letter-exchange': 'log_error',
            'x-expires': self.__x_expires,
            'x-message-ttl': self.__x_message_ttl,
        }
        queue = await channel.declare_queue(
            self.__queue_consume,
            durable=True,
            arguments=arguments,
        )
        routing_key = f'chatbot.{self.__queue_consume}'
        await queue.bind(
            exchange=self.__virtual_host,
            routing_key=routing_key,
        )
        return queue

    async def __connect_and_consume(
        self, amqp_url: str, process_message: Callable
    ) -> None:
        connection = await aio_pika.connect_robust(
            amqp_url, heartbeat=self.__heartbeat
        )
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=self.__prefetch_count)
            queue = await self.__declare_queue(channel)
            _logger.info('[x] Server inicializado! Aguardando solicitações RPC')
            async for message in queue:
                async with message.process():
                    await self.on_request(message.body, process_message)

    async def start_consume(self, process_message: Callable) -> None:
        await self.__initialize_router()
        amqp_url = self.__build_amqp_url()
        try:
            while True:
                try:
                    await self.__connect_and_consume(amqp_url, process_message)
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    _logger.error(
                        f'Erro no consumer: {e}. '
                        f'Reconectando em {self.__reconnect_interval}s...'
                    )
                    await asyncio.sleep(self.__reconnect_interval)
        finally:
            await self.cleanup()

    async def on_request(self, body: bytes, process_message: Callable):
        try:
            message = body.decode()
            message_json = json.loads(message)
            pure_message = await self.__transform_message(message_json)
            await process_message(pure_message)
        except Exception as e:
            _logger.error(f'Erro ao processar mensagem: {e}')

    async def __transform_message(self, message: dict) -> UserCall:
        user_state = message.get('user_state', {})
        message_data = message.get('message', {})
        observation = user_state.get('observation', "{}")

        if isinstance(observation, str):
            observation = json.loads(observation)

        user_state_models = UserState.from_dict(user_state)
        message_models = Message.from_dict(message_data)

        platform_state_data = message.get('platform_state', {})
        if not isinstance(platform_state_data, dict):
            platform_state_data = None
        platform_state = PlatformState.from_dict(platform_state_data)

        router_client = await self.__initialize_router()

        usercall = UserCall(
            user_state=user_state_models,
            message=message_models,
            router_client=router_client,
            platform_state=platform_state,
        )

        return usercall

    async def cleanup(self):
        """Libera recursos do cliente HTTP."""
        if self.__router_client:
            await self.__router_client.close()
            self.__router_client = None
            _logger.info('RouterHTTPClient fechado')

    def reprer(self):
        console = Console()

        title_text = Text('ChatGraph', style='bold red', justify='center')
        title_panel = Panel.fit(
            title_text, title=' ', border_style='bold red', padding=(1, 4)
        )

        separator = Text(
            '🐇🐇🐇 RabbitMessageConsumer 📨📨📨',
            style='cyan',
            justify='center',
        )

        table = Table(
            show_header=True,
            header_style='bold magenta',
            title='RabbitMQ Consumer',
        )
        table.add_column(
            'Atributo', justify='center', style='cyan', no_wrap=True
        )
        table.add_column('Valor', justify='center', style='magenta')

        table.add_row('Virtual Host', self.__virtual_host)
        table.add_row('Prefetch Count', str(self.__prefetch_count))
        table.add_row('Queue Consume', self.__queue_consume)
        table.add_row('AMQP URL', self.__amqp_url)
        table.add_row('Rabbit Username', self.__credentials.username)
        table.add_row('Rabbit Password', '******')
        table.add_row('Router URL', self.__router_url)

        console.print(title_panel, justify='center')
        console.print(separator, justify='center')
        console.print(table, justify='center')
