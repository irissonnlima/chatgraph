import asyncio
import concurrent.futures
import json
import logging
from typing import Optional

from chatgraph.logger.user_logger import UserLoggerManager
from chatgraph.models.message import (
    File,
    Message,
    MessageTypes,
)
from chatgraph.models.userstate import Menu, User, UserState
from chatgraph.services.router_http_client import RouterHTTPClient


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

    @property
    def logger(self) -> logging.Logger:
        return UserLoggerManager.get_user_logger(self.user_id, self.company_id)

    def __str__(self):
        return (
            f'UserCall(UserState={self.__user_state}, '
            f'Message={self.__message})'
        )

    async def __get_file_from_server(self, hash_id: str) -> Optional[File]:
        try:
            self.logger.debug(f"Buscando arquivo no servidor | hash={hash_id}")
            file = await self.__router_client.get_file(hash_id)
            if not file.url:
                self.logger.debug(f"Arquivo não encontrado no servidor | hash={hash_id}")
                return None
            self.logger.debug(f"Arquivo encontrado | hash={hash_id} | url={file.url}")
            return file
        except Exception as e:
            self.logger.error(f'Erro ao obter arquivo do servidor: {e}')
            return None

    async def __upload_file(
        self, file: File
    ) -> tuple[bool, str, Optional[File]]:
        try:
            self.logger.debug(f"Iniciando upload | arquivo={file.name}")
            uploaded_file = await self.__router_client.upload_file(file)
            self.logger.info(f"Upload concluído | arquivo={file.name}")
            return True, 'Upload successful', uploaded_file
        except Exception as e:
            self.logger.error(f'Erro ao enviar arquivo para o servidor: {e}')
            return False, str(e), None

    async def __check_file_for_send(self, file: str | File) -> File:
        self.logger.debug(f"Verificando arquivo para envio | arquivo={file.name if isinstance(file, File) else file}")
        try:
            if isinstance(file, str):
                file = File(name=file)

            await file.load_file()
        except Exception as e:
            raise ValueError('Erro ao criar File: ' + str(e))

        if not file.hash_id:
            raise ValueError('Hash do arquivo não gerado.')

        if not file.bytes_data:
            raise ValueError('Dados do arquivo em bytes não carregados.')

        existing_file = await self.__get_file_from_server(file.hash_id)
        if existing_file:
            self.logger.debug(f"Arquivo já existente no servidor | hash={file.hash_id}")
            return existing_file

        self.logger.debug(f"Arquivo não encontrado no servidor, iniciando upload | hash={file.hash_id}")
        status, msg, uploaded = await self.__upload_file(file)
        if not status or not uploaded:
            raise ValueError('Erro ao enviar arquivo: ' + msg)

        return uploaded

    async def __send(self, message: Message) -> None:
        try:
            self.logger.debug(f"Enviando mensagem | user={self.user_id} | company={self.company_id} | tipo={message.type if hasattr(message, 'type') else 'N/A'}")
            response = await self.__router_client.send_message(
                message, self.__user_state
            )

            if response:
                self.logger.debug(f"Mensagem enviada com sucesso | user={self.user_id}")

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
        self.logger.debug(f"send() chamado | tipo={type(message).__name__}")
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
        self,
        end_action_id: str = '',
        end_action_name: str = '',
        observation: str = '',
    ) -> None:
        try:
            self.logger.info(f"Encerrando chat | user={self.user_id} | company={self.company_id} | end_action_id='{end_action_id}' | end_action_name='{end_action_name}'")
            end_action = await self.__router_client.get_end_action(
                end_action_id,
                end_action_name,
            )

            if observation:
                end_action.observation = observation

            await self.__router_client.end_chat(
                self.__user_state.chat_id,
                end_action,
                'chatgraph',
            )
            self.logger.info(f"Chat encerrado com sucesso | user={self.user_id}")
        except Exception as e:
            raise ValueError(
                'Erro ao realizar ação de encerramento: ' + str(e)
            )

    async def set_observation(self, observation: str = '') -> None:
        try:
            self.logger.debug(f"Atualizando observação da sessão | user={self.user_id}")
            if not observation and self.__user_state.observation:
                observation = self.__user_state.observation

            await self.__router_client.update_session_observation(
                self.__user_state.chat_id,
                observation,
            )
        except Exception as e:
            self.logger.error(f'Erro ao atualizar observação: {e}')

    async def add_observation(self, observation: dict) -> None:
        try:
            self.logger.debug(f"Adicionando observação | user={self.user_id} | chaves={list(observation.keys())}")
            current_observation = self.observation
            current_observation.update(observation)
            self.__user_state.observation = json.dumps(current_observation)
            await self.set_observation()
        except Exception as e:
            raise ValueError(f'Erro ao adicionar observação: {e}')

    async def set_route(self, current_route: str):
        try:
            self.logger.debug(f"Atualizando rota | user={self.user_id} | nova_rota='{current_route}'")
            if not current_route:
                raise ValueError('Rota atual não pode ser vazia.')

            if not self.__user_state.route:
                self.__user_state.route = 'start'

            self.__user_state.route += f'.{current_route}'
            await self.__router_client.set_session_route(
                self.__user_state.chat_id,
                current_route,
            )
            self.logger.info(f"Rota atualizada | user={self.user_id} | rota='{self.__user_state.route}'")
        except Exception as e:
            raise ValueError(f'Erro ao atualizar rota: {e}')

    async def transfer_to_menu(
        self,
        menu_name: str,
        user_message: str,
        route: str = '',
    ) -> None:
        try:
            self.logger.info(f"Transferindo para menu | user={self.user_id} | menu='{menu_name}'")
            if not menu_name:
                raise ValueError('Menu de destino não pode ser vazio.')

            menu = Menu.from_name(menu_name)
            message = Message(text_message=user_message)

            await self.__router_client.transfer_to_menu(
                self.__user_state.chat_id,
                menu,
                message,
                route,
            )
        except Exception as e:
            raise ValueError(f'Erro ao transferir para menu: {e}')

    async def update_user_data(self, user: User) -> None:
        try:
            self.logger.debug(f"Atualizando dados do usuário | user={self.user_id}")
            await self.__router_client.update_user(user)
            self.__user_state.user = user
            self.logger.info(f"Dados do usuário atualizados | user={self.user_id}")
        except Exception as e:
            raise ValueError('Erro ao atualizar dados do usuário: ' + str(e))

    async def get_menu(
        self,
        name: Optional[str] = None,
        menu_id: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Optional[Menu]:
        try:
            self.logger.debug(f"Consultando menu | name={name!r} | id={menu_id}")
            menus = await self.__router_client.get_menus(
                menu_id=menu_id,
                name=name,
                description=description,
            )
            return menus[0] if menus else None
        except Exception as e:
            raise ValueError('Erro ao consultar menu: ' + str(e))

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
    def user(self) -> User:
        if not self.__user_state.user:
            return User()

        return self.__user_state.user

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
        loop.create_task(self.add_observation(observation))

    @content_message.setter
    def content_message(self, content_message: str):
        self.__content_message = content_message
