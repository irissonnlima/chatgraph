import json
import os
import hashlib

from chatgraph.services.router_http_client import RouterHTTPClient
from chatgraph.models.userstate import UserState, ChatID
from chatgraph.models.message import (
    Message,
    File,
    TextMessage,
    Button,
    MessageTypes,
)
from chatgraph.types.image import ImageData, ImageMessage, FileData
from typing import Optional
from datetime import datetime
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
        self.console = Console()

    def __str__(self):
        return (
            f'UserCall(UserState={self.__user_state}, '
            f'Message={self.__message})'
        )

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

        if isinstance(message, Message):
            if message.has_file():
                await self.__check_file_for_send(message.file.name)
            await self.__send(message)

        if isinstance(message, File):
            await self.__check_file_for_send(message.name)
            file_message = Message(file=message)
            await self.__send(file_message)

        else:
            raise ValueError('Tipo de mensagem inválido.')

    async def __get_file_from_server(self, hash_id: str) -> Optional[File]:
        try:
            file = await self.__router_client.get_file(hash_id)
            return file
        except Exception as e:
            self.console.print(f'Erro ao obter arquivo do servidor: {e}')
            return None

    async def __upload_file(self, file_data: bytes) -> tuple[bool, str]:
        try:
            await self.__router_client.upload_file(file_data)
            return True, 'Upload successful'
        except Exception as e:
            self.console.print(f'Erro ao enviar arquivo para o servidor: {e}')
            return False, str(e)

    async def __check_file_for_send(self, path_file: str) -> None:
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
            return

        uploaded, msg = await self.__upload_file(file.bytes_data)
        if not uploaded:
            raise ValueError('Erro ao enviar arquivo: ' + msg)

    async def __send_image(self, message: ImageMessage) -> None:
        dict_message = message.to_dict()
        dict_message['message']['chat_id'] = (
            self.__user_state.chat_id.to_dict()
        )
        response = self.__router_client.send_image(dict_message)

        if (
            not response.status
            and response.message != 'arquivo não encontrado'
        ):
            raise ValueError('Erro ao enviar imagem.')
        elif response.message == 'arquivo não encontrado':
            self.__upload_file(message.image)
            print('tentando enviar imagem novamente...')
            self.__send_image(message)

    async def __send(self, message: Message) -> None:
        dict_message = message.to_dict()
        dict_message['chat_id'] = self.__user_state.chatID.to_dict()
        response = self.__router_client.send_message(dict_message)

        if not response.status:
            raise ValueError('Erro ao enviar mensagem de texto.')

        if not response.status:
            raise ValueError('Erro ao enviar mensagem de botões.')

    async def end_chat(self, end_action_id: str) -> None:
        

        response = await self.__router_client.end_chat(
            self.__user_state.chat_id,
            end_action_id,
            'chatgraph',
        )

        if not response.status:
            raise ValueError('Erro ao encerrar o chat.')

    async def delete_user_state(self) -> None:
        response = self.__user_state.delete(self.__grpc_uri)

        if not response.status:
            raise ValueError('Erro ao deletar estado do usuário.')

    async def update_user_state(
        self,
        menu: str,
        route: str,
        observation: dict,
    ) -> None:
        self.__user_state.menu = menu
        self.__user_state.route = route
        self.__user_state.observation = observation
        self.__user_state.insert(self.__grpc_uri)

    @property
    def chatID(self):
        return self.__user_state.chatID

    @property
    def user_id(self):
        return self.__user_state.chatID.user_id

    @property
    def company_id(self):
        return self.__user_state.chatID.company_id

    @property
    def menu(self):
        return self.__user_state.menu

    @property
    def route(self):
        return self.__user_state.route

    @property
    def customer_id(self):
        return self.__user_state.customer_id

    @property
    def protocol(self):
        return self.__user_state.protocol

    @property
    def observation(self):
        return self.__user_state.observation

    @property
    def type_message(self):
        return self.__type_message

    @property
    def content_message(self):
        return self.__content_message

    @menu.setter
    def menu(self, menu):
        self.update_user_state(
            menu, self.__user_state.route, self.__user_state.observation
        )

    @route.setter
    def route(self, route):
        self.update_user_state(
            self.__user_state.menu, route, self.__user_state.observation
        )

    @observation.setter
    def observation(self, observation):
        self.update_user_state(
            self.__user_state.menu, self.__user_state.route, observation
        )

    @content_message.setter
    def content_message(self, content_message: str):
        self.__content_message = content_message
