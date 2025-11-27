import json
from chatgraph.services.router_http_client import RouterHTTPClient
from chatgraph.models.userstate import UserState
from chatgraph.models.message import (
    Message,
    File,
    MessageTypes,
)
from chatgraph.config import config
from typing import Optional


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
        verbose: Optional[bool] = None,
    ) -> None:
        self.type = type
        self.__message = message
        self.__user_state = user_state
        self.__router_client = router_client
        self.__content_message = self.__message.text_message.detail
        
        # Usar verbose do parâmetro ou da configuração global
        self.__verbose = verbose if verbose is not None else config.verbose

    def __str__(self):
        return (
            f'UserCall(UserState={self.__user_state}, '
            f'Message={self.__message})'
        )

    def _log(self, message: str, level: str = 'INFO'):
        """Helper para logs condicionais baseado na configuração."""
        if self.__verbose:
            config.print(message, level)

    async def __get_file_from_server(self, hash_id: str) -> Optional[File]:
        """Busca arquivo no servidor pelo hash ID."""
        try:
            self._log(
                f'[cyan]→ Buscando arquivo {hash_id[:8]}... no servidor[/cyan]'
            )
            file = await self.__router_client.get_file(hash_id)
            if not file.url:
                self._log(
                    '[yellow]⚠ Arquivo não possui URL válida[/yellow]'
                )
                return None
            self._log(
                f'[green]✓ Arquivo encontrado: {file.name}[/green]'
            )
            return file
        except Exception as e:
            self._log(
                f'[red]✗ Erro ao obter arquivo do servidor: {e}[/red]'
            )
            return None

    async def __upload_file(
        self, file_data: bytes
    ) -> tuple[bool, str, Optional[File]]:
        """Faz upload de arquivo para o servidor."""
        try:
            file_size_kb = len(file_data) / 1024
            self._log(
                f'[cyan]↑ Fazendo upload de arquivo ({file_size_kb:.2f} KB)...[/cyan]'
            )
            file = await self.__router_client.upload_file(file_data)
            self._log('[green]✓ Upload concluído com sucesso[/green]')
            return True, 'Upload successful', file
        except Exception as e:
            self._log(
                f'[red]✗ Erro ao enviar arquivo para o servidor: {e}[/red]'
            )
            return False, str(e), None

    async def __check_file_for_send(self, path_file: str) -> File:
        """Valida arquivo e faz upload se necessário."""
        self._log(f'[cyan]→ Preparando arquivo: {path_file}[/cyan]')

        try:
            file = File(name=path_file)
            await file.load_file()
        except Exception as e:
            self._log(f'[red]✗ Erro ao criar File: {e}[/red]')
            raise ValueError('Erro ao criar File: ' + str(e))

        if not file.hash_id:
            self._log('[red]✗ Hash do arquivo não gerado[/red]')
            raise ValueError('Hash do arquivo não gerado.')

        if not file.bytes_data:
            self._log(
                '[red]✗ Dados do arquivo em bytes não carregados[/red]'
            )
            raise ValueError('Dados do arquivo em bytes não carregados.')

        self._log(
            f'[cyan]→ Verificando se arquivo já existe no servidor...[/cyan]'
        )
        existing_file = await self.__get_file_from_server(file.hash_id)
        if existing_file:
            self._log(
                '[green]✓ Arquivo já existe no servidor, reutilizando[/green]'
            )
            return existing_file

        self._log(
            '[yellow]⚠ Arquivo não encontrado, fazendo upload...[/yellow]'
        )
        status, msg, uploaded = await self.__upload_file(file.bytes_data)
        if not status or not uploaded:
            self._log(f'[red]✗ Erro ao enviar arquivo: {msg}[/red]')
            raise ValueError('Erro ao enviar arquivo: ' + msg)

        return uploaded

    async def __send(self, message: Message) -> None:
        """Envia mensagem via RouterClient."""
        try:
            msg_preview = (
                str(message.text_message.detail)[:50]
                if message.text_message
                else 'arquivo'
            )
            self._log(
                f'[cyan]→ Enviando mensagem: "{msg_preview}..."[/cyan]'
            )

            response = await self.__router_client.send_message(
                message, self.__user_state
            )

            if response:
                status = response.get('status', False)
                if status:
                    self._log(
                        '[green]✓ Mensagem enviada com sucesso[/green]'
                    )
                else:
                    msg = response.get('message', 'Erro desconhecido')
                    self._log(
                        f'[yellow]⚠ Mensagem enviada mas com aviso: {msg}[/yellow]'
                    )

        except Exception as e:
            self._log(f'[red]✗ Erro ao enviar mensagem: {e}[/red]')
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
            self._log(
                f'[dim]→ Processando mensagem de texto simples[/dim]'
            )
            msg = Message(str(message))
            await self.__send(msg)
            return

        if isinstance(message, Message):
            if message.has_file() and message.file:
                self._log(
                    '[dim]→ Mensagem contém arquivo anexado[/dim]'
                )
                message.file = await self.__check_file_for_send(
                    message.file.name
                )
            await self.__send(message)
            return

        if isinstance(message, File):
            self._log('[dim]→ Processando envio de arquivo[/dim]')
            file = await self.__check_file_for_send(message.name)
            file_message = Message(file=file)
            await self.__send(file_message)
            return

        self._log(
            f'[red]✗ Tipo de mensagem inválido: {type(message)}[/red]'
        )
        raise ValueError('Tipo de mensagem inválido.')

    async def end_chat(
        self, end_action_id: str = '', end_action_name: str = ''
    ) -> None:
        """Encerra o chat com tabulação."""
        try:
            self._log(
                f'[cyan]→ Buscando ação de encerramento: {end_action_id or end_action_name}[/cyan]'
            )
            end_action = await self.__router_client.get_end_action(
                end_action_id,
                end_action_name,
            )

            self._log('[cyan]→ Encerrando chat...[/cyan]')
            await self.__router_client.end_chat(
                self.__user_state.chat_id,
                end_action,
                'chatgraph',
            )
            self._log('[green]✓ Chat encerrado com sucesso[/green]')

        except Exception as e:
            self._log(f'[red]✗ Erro ao encerrar chat: {e}[/red]')
            raise ValueError(
                'Erro ao realizar ação de encerramento: ' + str(e)
            )

    async def set_observation(self, observation: str = '') -> None:
        """Atualiza observações da sessão."""
        try:
            if not observation and self.__user_state.observation:
                observation = self.__user_state.observation

            self._log(
                '[cyan]→ Atualizando observações da sessão...[/cyan]'
            )
            await self.__router_client.update_session_observation(
                self.__user_state.chat_id,
                observation,
            )
            self._log('[green]✓ Observações atualizadas[/green]')
        except Exception as e:
            self._log(
                f'[red]✗ Erro ao atualizar observação: {e}[/red]'
            )

    async def add_observation(self, observation: dict) -> None:
        """Adiciona dados às observações existentes."""
        try:
            self._log(
                f'[cyan]→ Adicionando observações: {list(observation.keys())}[/cyan]'
            )
            current_observation = self.observation
            current_observation.update(observation)
            self.__user_state.observation = json.dumps(current_observation)
            await self.set_observation()
        except Exception as e:
            self._log(
                f'[red]✗ Erro ao adicionar observação: {e}[/red]'
            )
            raise ValueError(f'Erro ao adicionar observação: {e}')

    async def set_route(self, current_route: str):
        """Atualiza rota da sessão."""
        try:
            if not current_route:
                self._log(
                    '[red]✗ Rota atual não pode ser vazia[/red]'
                )
                raise ValueError('Rota atual não pode ser vazia.')

            if not self.__user_state.route:
                self.__user_state.route = 'start'

            old_route = self.__user_state.route
            self.__user_state.route += f'.{current_route}'

            self._log(
                f'[cyan]→ Atualizando rota: {old_route} → {current_route}[/cyan]'
            )
            await self.__router_client.set_session_route(
                self.__user_state.chat_id,
                current_route,
            )
            self._log(
                f'[green]✓ Rota atualizada para: {current_route}[/green]'
            )
        except Exception as e:
            self._log(f'[red]✗ Erro ao atualizar rota: {e}[/red]')
            raise ValueError(f'Erro ao atualizar rota: {e}')

    async def transfer_to_menu(self, menu: str, user_message: str) -> None:
        raise NotImplementedError(
            'transfer_to_menu method is not implemented yet.'
        )

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
    async def observation(self, observation: dict):
        self.__user_state.observation = json.dumps(observation)
        await self.set_observation()

    @content_message.setter
    def content_message(self, content_message: str):
        self.__content_message = content_message
