import json
import asyncio
from logging import debug, info
import os
import aio_pika
from typing import Callable
from ..auth.credentials import Credential
from ..types.request_types import UserCall, UserState, ChatID
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
        grpc_uri: str,
        queue_consume: str,
        prefetch_count: int = 1,
        virtual_host: str = "/",
    ) -> None:
        self.__virtual_host = virtual_host
        self.__prefetch_count = prefetch_count
        self.__queue_consume = queue_consume
        self.__amqp_url = amqp_url
        self.__grpc_uri = grpc_uri
        self.__credentials = credential

    @classmethod
    def load_dotenv(
        cls,
        user_env: str = "RABBIT_USER",
        pass_env: str = "RABBIT_PASS",
        uri_env: str = "RABBIT_URI",
        queue_env: str = "RABBIT_QUEUE",
        prefetch_env: str = "RABBIT_PREFETCH",
        vhost_env: str = "RABBIT_VHOST",
        grpc_uri: str = "GRPC_URI",
    ) -> "MessageConsumer":
        username = os.getenv(user_env)
        password = os.getenv(pass_env)
        url = os.getenv(uri_env)
        queue = os.getenv(queue_env)
        prefetch = os.getenv(prefetch_env, 1)
        vhost = os.getenv(vhost_env, "/")
        grpc = os.getenv(grpc_uri)

        if not username or not password or not url or not queue or not grpc:
            raise ValueError("Corrija as variáveis de ambiente!")

        return cls(
            credential=Credential(username=username, password=password),
            amqp_url=url,
            queue_consume=queue,
            prefetch_count=int(prefetch),
            virtual_host=vhost,
            grpc_uri=grpc,
        )

    async def start_consume(self, process_message: Callable):
        try:
            user = quote(self.__credentials.username)
            pwd = quote(self.__credentials.password)
            vhost = quote(self.__virtual_host)
            uri = self.__amqp_url
            amqp_url = f"amqp://{user}:{pwd}@{uri}/{vhost}"
            connection = await aio_pika.connect_robust(amqp_url)

            async with connection:
                channel = await connection.channel()
                await channel.set_qos(prefetch_count=self.__prefetch_count)
                
                try:
                    queue = await channel.get_queue(self.__queue_consume, ensure=True)
                except aio_pika.exceptions.ChannelNotFoundEntity:
                    arguments = {
                        "x-dead-letter-exchange": "log_error",  # Dead Letter Exchange
                        "x-expires": 86400000,                 # Expiração da fila (em milissegundos)
                        "x-message-ttl": 300000                # Tempo de vida das mensagens (em milissegundos)
                    }
                    queue = await channel.declare_queue(self.__queue_consume, durable=True, arguments=arguments)
                
                info("[x] Server inicializado! Aguardando solicitações RPC")

                async for message in queue:
                    async with message.process():
                        await self.on_request(message.body, process_message)
        except Exception as e:
            print(f"Erro durante o consumo de mensagens: {e}")
            # Reiniciar a conexão em caso de falha
            # await self.start_consume(process_message)

    async def on_request(self, body: bytes, process_message: Callable):
        try:
            message = body.decode()
            message_json = json.loads(message)
            pure_message = self.__transform_message(message_json)
            print(pure_message)
            await process_message(pure_message)
        except Exception as e:
            debug(f"Erro ao processar mensagem: {e}")

    def __transform_message(self, message: dict) -> UserCall:
        user_state = message.get("user_state", {})
        observation = user_state.get("observation", {})
        if isinstance(observation, str):
            observation = json.loads(observation)

        usercall = UserCall(
            user_state=UserState(
                chatID=ChatID(
                    user_id=user_state['chat_id'].get("user_id", ""),
                    company_id=user_state['chat_id'].get("company_id", ""),
                ),
                menu=user_state.get("menu", ""),
                route=user_state.get("route", ""),
                protocol=user_state.get("protocol", ""),
                observation=observation,
            ),
            type_message=message.get("type_message", ""),
            content_message=message.get("content_message", ""),
            grpc_uri=self.__grpc_uri,
        )
        
        return usercall

    def reprer(self):
        console = Console()

        title_text = Text("ChatGraph", style="bold red", justify="center")
        title_panel = Panel.fit(title_text, title=" ", border_style="bold red", padding=(1, 4))

        separator = Text("🐇🐇🐇 RabbitMessageConsumer 📨📨📨", style="cyan", justify="center")

        table = Table(show_header=True, header_style="bold magenta", title="RabbitMQ Consumer")
        table.add_column("Atributo", justify="center", style="cyan", no_wrap=True)
        table.add_column("Valor", justify="center", style="magenta")

        table.add_row("Virtual Host", self.__virtual_host)
        table.add_row("Prefetch Count", str(self.__prefetch_count))
        table.add_row("Queue Consume", self.__queue_consume)
        table.add_row("AMQP URL", self.__amqp_url)
        table.add_row("Username", self.__credentials.username)
        table.add_row("Password", "******")

        console.print(title_panel, justify="center")
        console.print(separator, justify="center")
        console.print(table, justify="center")
