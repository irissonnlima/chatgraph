import json
import asyncio
from chatgraph.services.router_http_client import RouterHTTPClient
from chatgraph.models.userstate import UserState
from chatgraph.models.message import (
    Message,
    File,
    MessageTypes,
)
from typing import Optional
from rich.console import Console


class UserCall:
    """
    Representa uma mensagem recebida ou enviada pelo chatbot.

    Atributos:
        type (str): O tipo da mensagem (por exemplo, texto, imagem, etc.).
        text (str): O conteúdo textual da mensagem.
        UserState (UserState): O estado do usuário.
        channel (str): O canal pelo qual a mensagem foi enviada ou recebida (por exemplo, WhatsApp, SMS, etc.).
        customer_phone (str): O número de telefone do cliente.
        company_phone (str): O número de telefone da empresa que está enviando ou recebendo a mensagem.
        status (Optional[str]): O status da mensagem (por exemplo, enviada, recebida, lida, etc.). Este campo é opcional.
    """

    def __init__(
        self,
        user_state: UserState,
        message: Message,
        router_client: RouterHTTPClient,
    ) -> None:
        self.type = type
        self.__message = message
        self.__user_state = user_state
        self.__router_client = router_client
        self.__content_message = self.__message.text_message.detail
        self.console = Console()

    def __str__(self):
        return (
            f'UserCall(UserState={self.__user_state}, '
            f'Message={self.__message})'
        )

    async def __get_file_from_server(self, hash_id: str) -> Optional[File]:
        try:
            file = await self.__router_client.get_file(hash_id)
            if not file.url:
                return None
            return file
        except Exception as e:
            self.console.print(f'Erro ao obter arquivo do servidor: {e}')
            return None

    async def __upload_file(
        self, file_data: bytes
    ) -> tuple[bool, str, Optional[File]]:
        try:
            file = await self.__router_client.upload_file(file_data)
            return True, 'Upload successful', file
        except Exception as e:
            self.console.print(f'Erro ao enviar arquivo para o servidor: {e}')
            return False, str(e), None

    async def __check_file_for_send(self, path_file: str) -> File:
        try:
            file = File(name=path_file)
            await file.load_file()
        except Exception as e:
            raise ValueError('Erro ao criar File: ' + str(e))

        if not file.hash_id:
            raise ValueError('Hash do arquivo não gerado.')

        if not file.bytes_data:
            raise ValueError('Dados do arquivo em bytes não carregados.')

        existing_file = await self.__get_file_from_server(file.hash_id)
        if existing_file:
            return existing_file

        status, msg, uploaded = await self.__upload_file(file.bytes_data)
        if not status or not uploaded:
            raise ValueError('Erro ao enviar arquivo: ' + msg)

        return uploaded

    async def __send(self, message: Message) -> None:
        try:
            response = await self.__router_client.send_message(
                message, self.__user_state
            )

            if response:
                self.console.print(f'Mensagem enviada com sucesso: {response}')

            await asyncio.sleep(0.1)
        except Exception as e:
            raise Exception(f'Erro ao enviar mensagem: {e}')

    async def send(
        self,
        message: MessageTypes | Message | File,
    ) -> None:
        """
        Envia uma mensagem ao cliente.

        Args:
            message (Message|Button|ListElements): A mensagem a ser enviada.
        """
        if isinstance(message, MessageTypes):
            msg = Message(str(message))
            await self.__send(msg)
            return

        if isinstance(message, Message):
            if message.has_file() and message.file:
                message.file = await self.__check_file_for_send(
                    message.file.name
                )
            await self.__send(message)
            return

        if isinstance(message, File):
            file = await self.__check_file_for_send(message.name)
            file_message = Message(file=file)
            await self.__send(file_message)
            return

        raise ValueError('Tipo de mensagem inválido.')

    async def end_chat(
        self, end_action_id: str = '', end_action_name: str = ''
    ) -> None:
        try:
            end_action = await self.__router_client.get_end_action(
                end_action_id,
                end_action_name,
            )

            await self.__router_client.end_chat(
                self.__user_state.chat_id,
                end_action,
                'chatgraph',
            )

        except Exception as e:
            raise ValueError(
                'Erro ao realizar ação de encerramento: ' + str(e)
            )

    async def set_observation(self, observation: str = '') -> None:
        try:
            if not observation and self.__user_state.observation:
                observation = self.__user_state.observation

            await self.__router_client.update_session_observation(
                self.__user_state.chat_id,
                observation,
            )
        except Exception as e:
            self.console.print(f'Erro ao atualizar observação: {e}')

    async def add_observation(self, observation: dict) -> None:
        try:
            current_observation = self.observation
            current_observation.update(observation)
            self.__user_state.observation = json.dumps(current_observation)
            await self.set_observation()
        except Exception as e:
            raise ValueError(f'Erro ao adicionar observação: {e}')

    async def set_route(self, current_route: str):
        try:
            if not current_route:
                raise ValueError('Rota atual não pode ser vazia.')

            if not self.__user_state.route:
                self.__user_state.route = 'start'

            self.__user_state.route += f'.{current_route}'
            await self.__router_client.set_session_route(
                self.__user_state.chat_id,
                current_route,
            )
        except Exception as e:
            raise ValueError(f'Erro ao atualizar rota: {e}')

    async def transfer_to_menu(self, menu: str, user_message: str) -> None:
        raise NotImplementedError(
            'transfer_to_menu method is not implemented yet.'
        )

    async def insert(self, userstate: UserState) -> None:
        try:
            response = await self.__router_client.star(
                message, self.__user_state
            )

            if response:
                self.console.print(f'Mensagem enviada com sucesso: {response}')

            await asyncio.sleep(0.1)
        except Exception as e:
            raise Exception(f'Erro ao enviar mensagem: {e}')
 

    @property
    def chatID(self):
        return self.__user_state.chat_id

    @property
    def user_id(self):
        return self.__user_state.chat_id.user_id

    @property
    def company_id(self):
        return self.__user_state.chat_id.company_id

    @property
    def menu(self):
        return self.__user_state.menu

    @property
    def route(self):
        return self.__user_state.route

    @property
    def observation(self):
        return self.__user_state.observation_dict

    @property
    def content_message(self):
        return self.__content_message

    @observation.setter
    def observation(self, observation: dict):
        self.__user_state.observation = json.dumps(observation)
        loop = asyncio.get_event_loop()
        loop.create_task(self.set_observation())

    @content_message.setter
    def content_message(self, content_message: str):
        self.__content_message = content_message
