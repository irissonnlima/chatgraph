import json
from logging import info
import os
import aio_pika
from typing import Callable
from ..auth.credentials import Credential
from ..models.message import Message
from ..models.userstate import UserState
from ..services.router_http_client import RouterHTTPClient
from ..types.usercall import UserCall
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from urllib.parse import quote


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
    ) -> None:
        self.__virtual_host = virtual_host
        self.__prefetch_count = prefetch_count
        self.__queue_consume = queue_consume
        self.__amqp_url = amqp_url
        self.__router_url = router_url
        self.__router_token = router_token
        self.__credentials = credential
        self.__router_client = None

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
    ) -> 'MessageConsumer':
        username = os.getenv(user_env)
        password = os.getenv(pass_env)
        url = os.getenv(uri_env)
        queue = os.getenv(queue_env)
        prefetch = os.getenv(prefetch_env, '1')
        vhost = os.getenv(vhost_env, '/')
        router_url = os.getenv(router_env)
        router_token = os.getenv(router_token_env)

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

    async def start_consume(self, process_message: Callable):
        try:
            # Inicializar cliente HTTP uma única vez
            await self.__initialize_router()

            user = quote(self.__credentials.username)
            pwd = quote(self.__credentials.password)
            vhost = quote(self.__virtual_host)
            uri = self.__amqp_url
            amqp_url = f'amqp://{user}:{pwd}@{uri}/{vhost}'
            connection = await aio_pika.connect_robust(amqp_url)

            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=self.__prefetch_count)

                try:
                    queue = await channel.get_queue(
                        self.__queue_consume, ensure=True
                    )
                except aio_pika.exceptions.ChannelNotFoundEntity:
                    arguments = {
                        'x-dead-letter-exchange': 'log_error',  # Dead Letter Exchange
                        'x-expires': 86400000,  # Expiração da fila (em milissegundos)
                        'x-message-ttl': 300000,  # Tempo de vida das mensagens (em milissegundos)
                    }
                    queue = await channel.declare_queue(
                        self.__queue_consume,
                        durable=True,
                        arguments=arguments,
                    )

                info('[x] Server inicializado! Aguardando solicitações RPC')

                async for message in queue:
                    async with message.process():
                        await self.on_request(message.body, process_message)

        except Exception as e:
            print(f'Erro durante o consumo de mensagens: {e}')
            # Reiniciar a conexão em caso de falha
            # await self.start_consume(process_message)
        finally:
            # Fechar cliente HTTP quando o consumer parar
            await self.cleanup()

    async def on_request(self, body: bytes, process_message: Callable):
        try:
            message = body.decode()
            message_json = json.loads(message)
            pure_message = await self.__transform_message(message_json)
            await process_message(pure_message)
        except Exception as e:
            print(f'Erro ao processar mensagem: {e}')

    async def __transform_message(self, message: dict) -> UserCall:
        user_state = message.get('user_state', {})
        message_data = message.get('message', {})
        observation = user_state.get('observation', {})

        if isinstance(observation, str):
            observation = json.loads(observation)

        user_state_models = UserState.from_dict(user_state)
        message_models = Message.from_dict(message_data)

        # Reutilizar o mesmo cliente para todas as mensagens
        router_client = await self.__initialize_router()

        usercall = UserCall(
            user_state=user_state_models,
            message=message_models,
            router_client=router_client,
        )

        return usercall

    async def cleanup(self):
        """Libera recursos do cliente HTTP."""
        if self.__router_client:
            await self.__router_client.close()
            self.__router_client = None
            print('✓ RouterHTTPClient fechado')

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
