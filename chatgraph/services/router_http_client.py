from typing import Any, Dict, Optional

import httpx

from ..models.userstate import UserState, ChatID, Menu, User
from ..models.message import Message, File, Button, TextMessage


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

        async with self._client as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            response_data = response.json()
            status = response_data.get('status')
            message = response_data.get('message')
            sessions_data = response_data.get('data', [])

            if not status:
                raise Exception(f'Erro ao buscar as Sessões: {message}')

            sessions = [UserState.from_dict(item) for item in sessions_data]
            return sessions

        return []

    async def get_session_by_chat_id(
        self,
        chat_id: ChatID,
    ) -> Optional[UserState]:
        endpoint = '/session/'
        params = {
            'user_id': chat_id.user_id,
            'company_id': chat_id.company_id,
        }

        async with self._client as client:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            response_data = response.json()
            status = response_data.get('status')
            message = response_data.get('message')
            session_data = response_data.get('data')

            if not status:
                raise Exception(f'Erro ao buscar a Sessão: {message}')

            return UserState.from_dict(session_data)

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

        async with self._client as client:
            response = await client.post(
                endpoint,
                json=user_state.to_dict(),
            )
            response.raise_for_status()
            response_data = response.json()
            status = response_data.get('status')
            message = response_data.get('message')

            if not status:
                raise Exception(f'Erro ao iniciar sessão: {message}')

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

        async with self._client as client:
            payload = {
                'message': message_data.to_dict(),
                'user_state': user_state.to_dict(),
            }
            response = await client.post(
                endpoint,
                json=payload,
            )
            response.raise_for_status()
            response_data = response.json()
            status = response_data.get('status')
            message = response_data.get('message')

            if not status:
                raise Exception(f'Erro ao enviar mensagem: {message}')

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

        async with self._client as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            response_data = response.json()
            status = response_data.get('status')
            message = response_data.get('message')
            file_data = response_data.get('data')

            if not status:
                raise Exception(f'Erro ao buscar arquivo: {message}')

            return File.from_dict(file_data)

    async def upload_file(self, file_data: bytes) -> Any:
        """
        Faz upload de um arquivo (imagem) para o servidor.

        Args:
            file_data: Dicionário contendo os dados do arquivo:
                - file_type: Tipo do arquivo ("file" ou "link")
                - file_content: Bytes do arquivo (se type="file")
                - file_extension: Extensão do arquivo (se type="file")
                - file_url: URL do arquivo (se type="link")
                - expiration: Data de expiração (opcional)

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        endpoint = '/files/upload/'
        async with self._client as client:
            payload = {
                'content': file_data,
            }
            response = await client.post(
                endpoint,
                files=payload,
            )
            response.raise_for_status()
            response_data = response.json()
            status = response_data.get('status')
            message = response_data.get('message')

            if not status:
                raise Exception(f'Erro ao fazer upload do arquivo: {message}')

            return response_data

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

        async with self._client as client:
            response = await client.delete(endpoint)
            response.raise_for_status()
            response_data = response.json()
            status = response_data.get('status')
            message = response_data.get('message')

            if not status:
                raise Exception(f'Erro ao deletar arquivo: {message}')

            return response_data

    # ToDo Methods
    async def transfer_to_menu(self, transfer_data: Dict[str, Any]) -> Any:
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
        pass

    async def end_chat(self, end_data: Dict[str, Any]) -> Any:
        """
        Encerra o atendimento com tabulação.

        Args:
            end_data: Dicionário contendo:
                - chat_id: ID do chat (user_id, company_id)
                - tabulation_id: ID da tabulação de encerramento
                - observation: Observação sobre o encerramento

        Returns:
            Objeto de resposta com atributo 'status' indicando sucesso/falha.

        Raises:
            Exception: Se houver erro na comunicação.
        """
        pass
