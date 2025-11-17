"""
Testes para o RouterHTTPClient.

Este módulo contém testes unitários para verificar a inicialização
e funcionamento do cliente HTTP de roteamento.
"""

import httpx
import pytest

from chatgraph.services.router_http_client import RouterHTTPClient
from chatgraph.models.userstate import ChatID, UserState
from chatgraph.models.message import Message

@pytest.mark.unit
class TestRouterHTTPClientInit:
    """Testes para inicialização do RouterHTTPClient."""

    def test_init_with_basic_params(self, http_client_base_url):
        """Testa inicialização com parâmetros básicos."""
        client = RouterHTTPClient(base_url=http_client_base_url)

        assert client.base_url == http_client_base_url
        assert client.timeout == 30.0
        assert isinstance(client._client, httpx.AsyncClient)

    def test_init_with_trailing_slash(self, http_client_base_url):
        """Testa que trailing slash é removido da base_url."""
        url_with_slash = f'{http_client_base_url}/'
        client = RouterHTTPClient(base_url=url_with_slash)

        assert client.base_url == http_client_base_url

    def test_init_with_auth(self, http_client_config):
        """Testa inicialização com autenticação."""
        client = RouterHTTPClient(
            base_url=http_client_config['base_url'],
            username=http_client_config['username'],
            password=http_client_config['password'],
        )

        assert client.base_url == http_client_config['base_url']
        assert client._client.auth is not None
        assert isinstance(client._client.auth, httpx.BasicAuth)

    def test_init_with_custom_timeout(self, http_client_base_url):
        """Testa inicialização com timeout customizado."""
        custom_timeout = 60.0
        client = RouterHTTPClient(
            base_url=http_client_base_url, timeout=custom_timeout
        )

        assert client.timeout == custom_timeout

    def test_client_has_correct_headers(self, http_client_base_url):
        """Testa que o cliente tem os headers corretos."""
        client = RouterHTTPClient(base_url=http_client_base_url)

        headers = client._client.headers
        assert headers['Accept'] == 'application/json'

    def test_client_base_url_is_set(self, http_client_base_url):
        """Testa que o cliente AsyncClient tem a base_url configurada."""
        client = RouterHTTPClient(base_url=http_client_base_url)

        # httpx adiciona automaticamente uma barra final à base_url
        expected_url = http_client_base_url.rstrip('/') + '/'
        assert str(client._client.base_url) == expected_url

@pytest.mark.unit
class TestRouterHTTPClientContextManager:
    """Testes para uso como context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self, http_client_base_url):
        """Testa uso como context manager."""
        async with RouterHTTPClient(base_url=http_client_base_url) as client:
            assert isinstance(client, RouterHTTPClient)
            assert isinstance(client._client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_close_method(self, http_client_base_url):
        """Testa método close."""
        client = RouterHTTPClient(base_url=http_client_base_url)

        assert not client._client.is_closed

        await client.close()

        assert client._client.is_closed

@pytest.mark.unit
class TestRouterHTTPClientSessions:
    """Testes para métodos de sessões."""

    @pytest.mark.asyncio
    async def test_get_all_sessions_returns_list(
        self, http_client_base_url, respx_mock
    ):
        """Testa que get_all_sessions retorna uma lista."""
        # Mock da resposta da API
        respx_mock.get(f'{http_client_base_url}/session/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'Success',
                    'data': [
                        {
                            'chat_id': {
                                'user_id': 'user123',
                                'company_id': 'company456',
                            },
                            'platform': 'whatsapp',
                            'menu': {'name': 'Main'},
                            'route': 'start',
                        }
                    ],
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.get_all_sessions()
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].chat_id.user_id == 'user123'
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_all_sessions_empty_list(
        self, http_client_base_url, respx_mock
    ):
        """Testa get_all_sessions com lista vazia."""
        respx_mock.get(f'{http_client_base_url}/session/').mock(
            return_value=httpx.Response(
                200,
                json={'status': True, 'message': 'Success', 'data': []},
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.get_all_sessions()
            assert isinstance(result, list)
            assert len(result) == 0
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_all_sessions_error(
        self, http_client_base_url, respx_mock
    ):
        """Testa get_all_sessions com erro."""
        respx_mock.get(f'{http_client_base_url}/session/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': False,
                    'message': 'Database error',
                    'data': [],
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            with pytest.raises(Exception, match='Erro ao buscar as Sessões'):
                await client.get_all_sessions()
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_session_by_chat_id(
        self, http_client_base_url, respx_mock, sample_chat_id_data
    ):
        """Testa get_session_by_chat_id."""
        chat_id = ChatID.from_dict(sample_chat_id_data)

        respx_mock.get(
            f'{http_client_base_url}/session/?user_id={chat_id.user_id}&company_id={chat_id.company_id}'
        ).mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'Userstate retrieved successfully',
                    'data': {
                        'session_id': 22,
                        'chat_id': sample_chat_id_data,
                        'platform': 'whatsapp',
                        'menu': {'id': 1, 'name': 'Main'},
                        'user': {'name': 'Test User'},
                        'route': 'start',
                        'observation': '{}',
                        'last_update': '2025-11-16T07:42:47-03:00',
                        'dt_created': '2025-11-07T19:57:54-03:00',
                    },
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.get_session_by_chat_id(chat_id)
            assert result is not None
            assert result.chat_id.user_id == chat_id.user_id
            assert result.platform == 'whatsapp'
            assert result.session_id == 22
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_start_session(
        self, http_client_base_url, respx_mock, sample_user_state_data
    ):
        """Testa start_session."""
        user_state = UserState.from_dict(sample_user_state_data)

        respx_mock.post(f'{http_client_base_url}/session/start/').mock(
            return_value=httpx.Response(
                201,
                json={
                    'status': True,
                    'message': 'Session started',
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.start_session(user_state)
            assert result['status'] is True
            assert result['message'] == 'Session started'
        finally:
            await client.close()

@pytest.mark.unit
class TestRouterHTTPClientMessages:
    """Testes para métodos de mensagens."""

    @pytest.mark.asyncio
    async def test_send_message(
        self,
        http_client_base_url,
        respx_mock,
        sample_message_data,
        sample_user_state_data,
    ):
        """Testa send_message."""
        message = Message.from_dict(sample_message_data)
        user_state = UserState.from_dict(sample_user_state_data)

        respx_mock.post(f'{http_client_base_url}/messages/send/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'Message sent',
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.send_message(message, user_state)
            assert result['status'] is True
            assert result['message'] == 'Message sent'
        finally:
            await client.close()

@pytest.mark.unit
class TestRouterHTTPClientFiles:
    """Testes para métodos de arquivos."""

    @pytest.mark.asyncio
    async def test_get_file(
        self, http_client_base_url, respx_mock, sample_file_data
    ):
        """Testa get_file."""
        file_id = 'file123'

        respx_mock.get(f'{http_client_base_url}/files/{file_id}/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'File retrieved successfully',
                    'data': sample_file_data,
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.get_file(file_id)
            assert result.id == sample_file_data['id']
            assert result.name == sample_file_data['name']
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_upload_file(self, http_client_base_url, respx_mock):
        """Testa upload_file."""
        file_bytes = b'fake file content'

        respx_mock.post(f'{http_client_base_url}/files/upload/').mock(
            return_value=httpx.Response(
                201,
                json={
                    'status': True,
                    'message': 'File uploaded',
                    'file_id': 'file123',
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.upload_file(file_bytes)
            assert result['status'] is True
            assert result['message'] == 'File uploaded'
            assert 'file_id' in result
        finally:
            await client.close()
