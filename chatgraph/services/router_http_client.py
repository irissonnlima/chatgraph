from typing import Any, Dict, Optional

import httpx

from ..logger.user_logger import UserLoggerManager
from ..models.http_responses import RouterResponses
from ..models.userstate import UserState, ChatID, Menu, User
from ..models.message import Message, File
from ..models.actions import EndAction

_logger = UserLoggerManager.get_system_logger()


class RouterHTTPClient:
    """
    Cliente HTTP para serviços de roteamento de mensagens.

    Utiliza httpx.AsyncClient para comunicação assíncrona com o backend
    do sistema de chatbot, incluindo envio de mensagens, gerenciamento
    de estado e transferências de chat.
    """

    def __init__(
        self,
        base_url: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Inicializa o cliente HTTP.

        Args:
            base_url: URL base da API (ex: "https://api.example.com")
            username: Nome de usuário para autenticação (opcional)
            password: Senha para autenticação (opcional)
            timeout: Timeout para requisições em segundos (padrão: 30.0)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # Configurar autenticação básica se fornecida
        auth = None
        if username and password:
            auth = httpx.BasicAuth(username, password)

        # Criar cliente assíncrono
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=auth,
            timeout=httpx.Timeout(timeout),
            headers={
                'Accept': 'application/json',
                # 'Content-Type': 'application/json',
            },
            verify=False,
            trust_env=True,
            follow_redirects=True,
        )

    async def close(self):
        """Fecha a conexão do cliente HTTP."""
        await self._client.aclose()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    # Sessions Methods
    async def get_all_sessions(self) -> list[UserState]:
        """
        Obtém todas as sessões ativas.

        Returns:
            Lista de UserState com todas as sessões ativas.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/session/'

        _logger.debug(f"[get_all_sessions] GET {endpoint}")
        response = await self._client.get(endpoint)
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[get_all_sessions] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[get_all_sessions] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao buscar as Sessões: {response_data.message}'
            )

        if not isinstance(response_data.data, list):
            raise Exception('Resposta de sessões mal formatada.')

        sessions = [UserState.from_dict(item) for item in response_data.data]
        return sessions

    async def get_session_by_chat_id(
        self,
        chat_id: ChatID,
    ) -> Optional[UserState]:
        endpoint = '/session/'
        params = {
            'user_id': chat_id.user_id,
            'company_id': chat_id.company_id,
        }

        _logger.debug(f"[get_session_by_chat_id] GET {endpoint} | user={chat_id.user_id} | company={chat_id.company_id}")
        response = await self._client.get(endpoint, params=params)
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[get_session_by_chat_id] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[get_session_by_chat_id] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao buscar a Sessão: {response_data.message}'
            )

        if not isinstance(response_data.data, dict):
            return None

        return UserState.from_dict(response_data.data)

    async def start_session(self, user_state: UserState) -> Any:
        """
        Inicia uma nova sessão de chat.

        Args:
            user_state: Estado inicial do usuário.

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/session/start/'

        _logger.debug(f"[start_session] POST {endpoint}")
        response = await self._client.post(
            endpoint,
            json=user_state.to_dict(),
        )
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[start_session] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[start_session] Erro: {response_data.message}")
            raise Exception(f'Erro ao iniciar sessão: {response_data.message}')

        return response_data

    async def set_session_route(self, chat_id: ChatID, route: str) -> Any:
        """
        Atualiza a rota da sessão de chat.

        Args:
            chat_id: Identificador do chat.
            route: Nova rota para a sessão.

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/session/route/'

        payload = {
            'chat_id': chat_id.to_dict(),
            'route': route,
        }

        _logger.debug(f"[set_session_route] POST {endpoint} | route={route}")
        response = await self._client.post(
            endpoint,
            json=payload,
        )
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[set_session_route] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[set_session_route] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao atualizar rota da sessão: {response_data.message}'
            )

        return response_data

    async def update_session_observation(
        self,
        chat_id: ChatID,
        observation: str,
    ) -> Any:
        """
        Atualiza a observação da sessão de chat.

        Args:
            chat_id: Identificador do chat.
            observation: Nova observação para a sessão.

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/session/observation/'

        payload = {
            'chat_id': chat_id.to_dict(),
            'observation': observation,
        }

        _logger.debug(f"[update_session_observation] POST {endpoint}")
        response = await self._client.post(
            endpoint,
            json=payload,
        )
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[update_session_observation] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[update_session_observation] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao atualizar observação da sessão: '
                f'{response_data.message}'
            )

        return response_data

    # Messages Methods
    async def send_message(
        self,
        message_data: Message,
        user_state: UserState,
    ) -> Any:
        """
        Envia uma mensagem de texto ao usuário.

        Args:
            message_data: Dicionário contendo os dados da mensagem:
                - chat_id: ID do chat (user_id, company_id)
                - type: Tipo da mensagem
                - detail: Conteúdo da mensagem

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/messages/send/'

        payload = {
            'message': message_data.to_dict(),
            'user_state': user_state.to_dict(),
        }
        _logger.debug(f"[send_message] POST {endpoint}")
        response = await self._client.post(
            endpoint,
            json=payload,
        )
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[send_message] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[send_message] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao enviar mensagem: {response_data.message}'
            )

        return response_data

    # Files Methods
    async def get_file(self, file_id: str) -> File:
        """
        Obtém um arquivo (imagem) pelo ID.

        Args:
            file_id: ID único do arquivo.

        Returns:
            Objeto de resposta com atributos 'status' e 'file_content'.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = f'/files/{file_id}/'

        _logger.debug(f"[get_file] GET {endpoint}")
        response = await self._client.get(endpoint)
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[get_file] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[get_file] Erro: {response_data.message}")
            raise Exception(f'Erro ao buscar arquivo: {response_data.message}')

        if not isinstance(response_data.data, dict):
            raise Exception('Resposta de arquivo mal formatada.')

        return File.from_dict(response_data.data)

    async def upload_file(self, file: File) -> File:
        """
        Faz upload de um arquivo para o servidor.

        Args:
            file: Instância de File contendo:
                - name: Nome do arquivo
                - bytes_data: Bytes do arquivo
                - mime_type: Tipo MIME (opcional)
                - expires_after_days: Dias para expiração (opcional)

        Returns:
            Objeto File com dados do upload realizado.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/files/upload/'

        if not file.bytes_data:
            raise ValueError(
                'Arquivo não carregado. Execute file.load_file() primeiro.'
            )

        # Extrair nome e extensão do arquivo
        filename = file.name if file.name else 'arquivo'
        extension = file.extension() if file.extension() else ''

        # Preparar dados como multipart/form-data
        files = {
            'content': (
                filename,
                file.bytes_data,
                file.mime_type or 'application/octet-stream',
            )
        }

        # Dados adicionais como form data
        data = {
            'file_type': 'file',
            'file_extension': extension,
            'file_name': filename,
        }

        if file.expires_after_days > 0:
            data['expiration'] = str(file.expires_after_days)

        _logger.debug(f"[upload_file] POST {endpoint} | arquivo={filename}")
        response = await self._client.post(
            endpoint,
            files=files,
            # data=data,
        )
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[upload_file] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[upload_file] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao fazer upload do arquivo: {response_data.message}'
            )

        if not isinstance(response_data.data, dict):
            raise Exception('Resposta de upload de arquivo mal formatada.')

        uploaded_file = File.from_dict(response_data.data)
        return uploaded_file

    async def delete_file(self, file_id: str) -> Any:
        """
        Deleta um arquivo (imagem) pelo ID.

        Args:
            file_id: ID único do arquivo.

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = f'/files/{file_id}'

        _logger.debug(f"[delete_file] DELETE {endpoint}")
        response = await self._client.delete(endpoint)
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[delete_file] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[delete_file] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao deletar arquivo: {response_data.message}'
            )

        return response_data

    # EndAction Methods
    async def end_chat(
        self,
        chat_id: ChatID,
        end_action: EndAction,
        origin: str,
    ) -> Any:
        """
        Encerra o atendimento com tabulação.

        Args:
            end_data: Dicionário contendo:
                - chat_id: ID do chat (user_id, company_id)
                - end_action: ID da tabulação de encerramento
                - observation: Observação sobre o encerramento

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/session/end/'
        payload = {
            'chat_id': chat_id.to_dict(),
            'end_action': end_action.to_dict(),
            'origin': origin,
        }

        _logger.debug(f"[end_chat] POST {endpoint}")
        response = await self._client.post(
            endpoint,
            json=payload,
        )
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[end_chat] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[end_chat] Erro: {response_data.message}")
            raise Exception(f'Erro ao encerrar chat: {response_data.message}')

        return response_data

    async def get_end_action(
        self,
        end_action_id: str = '',
        end_action_name: str = '',
    ) -> Any:
        """
        Obtém uma ação de encerramento pelo ID.

        Args:
            end_action_id: ID único da ação de encerramento.

        Returns:
            Objeto de resposta com atributos 'status' e 'end_action'.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/end_actions/'
        params = {
            'id': end_action_id,
            'name': end_action_name,
        }

        _logger.debug(f"[get_end_action] GET {endpoint} | id={end_action_id} | name={end_action_name}")
        response = await self._client.get(endpoint, params=params)
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[get_end_action] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[get_end_action] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao buscar ação de encerramento: {response_data.message}'
            )

        if not isinstance(response_data.data, dict):
            raise Exception('Resposta de ação de encerramento mal formatada.')

        return EndAction.from_dict(response_data.data)

    # Menu Methods
    async def get_menus(
        self,
        menu_id: Optional[int] = None,
        name: Optional[str] = None,
        department_id: Optional[int] = None,
        description: Optional[str] = None,
        active: Optional[bool] = None,
        protection_level: Optional[str] = None,
    ) -> list[Menu]:
        endpoint = '/menus/'
        params = {}
        if menu_id is not None:
            params['id'] = menu_id
        if name is not None:
            params['name'] = name
        if department_id is not None:
            params['department_id'] = department_id
        if description is not None:
            params['description'] = description
        if active is not None:
            params['active'] = active
        if protection_level is not None:
            params['protection_level'] = protection_level

        _logger.debug(f"[get_menus] GET {endpoint} | params={params}")
        response = await self._client.get(endpoint, params=params)
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[get_menus] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[get_menus] Erro: {response_data.message}")
            raise Exception(f'Erro ao buscar menus: {response_data.message}')

        if not isinstance(response_data.data, list):
            raise Exception('Resposta de menus mal formatada.')

        return [Menu.from_dict(item) for item in response_data.data]

    # User Methods
    async def update_user(self, user: User) -> RouterResponses:
        endpoint = '/user'

        _logger.debug(f"[update_user] PATCH {endpoint}")
        response = await self._client.patch(endpoint, json=user.to_dict())
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[update_user] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[update_user] Erro: {response_data.message}")
            raise Exception(f'Erro ao atualizar usuário: {response_data.message}')

        return response_data

    # ToDo Methods
    async def transfer_to_menu(
        self,
        chat_id: ChatID,
        menu: Menu,
        mensagem: Message,
        route: str = '',
    ) -> Any:
        """
        Transfere o chat para outro menu do fluxo.

        Args:
            transfer_data: Dicionário contendo:
                - chat_id: ID do chat (user_id, company_id)
                - menu: Nome do menu de destino
                - user_message: Mensagem do usuário

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = 'messages/transfer_to_menu'

        payload = {
            'chat_id': chat_id.to_dict(),
            'menu_id': menu.name,
            'message': mensagem.to_dict(),
        }
        if route:
            payload['route'] = route

        _logger.debug(f"[transfer_to_menu] POST {endpoint} | menu={menu.name} | route={route or 'N/A'}")
        response = await self._client.post(
            endpoint,
            json=payload,
        )
        response_data = RouterResponses.from_dict(response.json())
        _logger.debug(f"[transfer_to_menu] Resposta: status_code={response.status_code} | ok={response_data.status}")

        if not response_data.status:
            _logger.error(f"[transfer_to_menu] Erro: {response_data.message}")
            raise Exception(
                f'Erro ao transferir para o menu: {response_data.message}'
            )

        return response_data
