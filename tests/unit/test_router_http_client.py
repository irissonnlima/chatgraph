"""
Testes para o RouterHTTPClient.

Este módulo contém testes unitários para verificar a inicialização
e funcionamento do cliente HTTP de roteamento.
"""

import httpx
import pytest

from chatgraph.models.message import File, Message
from chatgraph.models.platform_state import PlatformState
from chatgraph.models.userstate import (
    ChatID,
    Menu,
    User,
    UserData,
    UserIdentity,
    UserState,
)
from chatgraph.services.router_http_client import RouterHTTPClient


@pytest.mark.unit
class TestRouterHTTPClientInit:
    """Testes para inicialização do RouterHTTPClient."""

    def test_init_with_basic_params(self, http_client_base_url):
        """Testa inicialização com parâmetros básicos."""
        client = RouterHTTPClient(base_url=http_client_base_url)

        assert client.base_url == http_client_base_url
        assert client.timeout == 30.0
        assert isinstance(client._actions_client, httpx.AsyncClient)

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
        assert client._actions_client.auth is not None
        assert isinstance(client._actions_client.auth, httpx.BasicAuth)

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

        headers = client._actions_client.headers
        assert headers['Accept'] == 'application/json'

    def test_client_base_url_is_set(self, http_client_base_url):
        """Testa que o cliente AsyncClient tem a base_url configurada."""
        client = RouterHTTPClient(base_url=http_client_base_url)

        # httpx adiciona automaticamente uma barra final à base_url
        expected_url = http_client_base_url.rstrip('/') + '/'
        assert str(client._actions_client.base_url) == expected_url


@pytest.mark.unit
class TestRouterHTTPClientContextManager:
    """Testes para uso como context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self, http_client_base_url):
        """Testa uso como context manager."""
        async with RouterHTTPClient(base_url=http_client_base_url) as client:
            assert isinstance(client, RouterHTTPClient)
            assert isinstance(client._actions_client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_close_method(self, http_client_base_url):
        """Testa método close."""
        client = RouterHTTPClient(base_url=http_client_base_url)

        assert not client._actions_client.is_closed
        assert not client._id_positiva_client.is_closed

        await client.close()

        assert client._actions_client.is_closed
        assert client._id_positiva_client.is_closed


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
                    'data': [{
                        'session_id': 22,
                        'chat_id': sample_chat_id_data,
                        'platform': 'whatsapp',
                        'menu': {'id': 1, 'name': 'Main'},
                        'user': {'name': 'Test User'},
                        'route': 'start',
                        'observation': '{}',
                        'last_update': '2025-11-16T07:42:47-03:00',
                        'dt_created': '2025-11-07T19:57:54-03:00',
                    }],
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
            assert result.status is True
            assert result.message == 'Session started'
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
            assert result.status is True
            assert result.message == 'Message sent'
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_send_message_with_platform_state(
        self,
        http_client_base_url,
        respx_mock,
        sample_message_data,
        sample_user_state_data,
    ):
        message = Message.from_dict(sample_message_data)
        user_state = UserState.from_dict(sample_user_state_data)
        ps = PlatformState(data={
            'session_id': 123,
            'customer_id': 'CUST001',
            'platform': 'whatsapp_enterprise',
            'protocol': 'PROTO001',
            'campaign': 'CAMPANHA.TESTE',
        })

        respx_mock.post(f'{http_client_base_url}/messages/send/').mock(
            return_value=httpx.Response(
                200,
                json={'status': True, 'message': 'Message sent'},
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.send_message(
                message, user_state, platform_state=ps
            )
            assert result.status is True

            import json
            body = json.loads(respx_mock.calls.last.request.content)
            assert 'platform_state' in body
            assert body['platform_state']['session_id'] == 123
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_send_message_without_platform_state(
        self,
        http_client_base_url,
        respx_mock,
        sample_message_data,
        sample_user_state_data,
    ):
        message = Message.from_dict(sample_message_data)
        user_state = UserState.from_dict(sample_user_state_data)
        ps = PlatformState(data={})

        respx_mock.post(f'{http_client_base_url}/messages/send/').mock(
            return_value=httpx.Response(
                200,
                json={'status': True, 'message': 'Message sent'},
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.send_message(
                message, user_state, platform_state=ps
            )
            assert result.status is True

            import json
            body = json.loads(respx_mock.calls.last.request.content)
            assert 'platform_state' not in body
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
        file = File(bytes_data=b'fake file content', name='test.txt')

        respx_mock.post(f'{http_client_base_url}/files/upload/').mock(
            return_value=httpx.Response(
                201,
                json={
                    'status': True,
                    'message': 'File uploaded',
                    'data': {
                        'id': 'file123',
                        'name': 'test.txt',
                        'url': 'https://example.com/test.txt',
                        'mime_type': 'application/octet-stream',
                        'size': 17,
                    },
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.upload_file(file)
            assert result.id == 'file123'
            assert result.name == 'test.txt'
        finally:
            await client.close()


@pytest.mark.unit
class TestGetMenus:
    """Testes para o método get_menus."""

    @pytest.mark.asyncio
    async def test_get_menus_returns_list(
        self, http_client_base_url, respx_mock, sample_menu_data
    ):
        respx_mock.get(f'{http_client_base_url}/menus/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'Success',
                    'data': [sample_menu_data],
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.get_menus()
            assert isinstance(result, list)
            assert len(result) == 1
            assert isinstance(result[0], Menu)
            assert result[0].id == sample_menu_data['id']
            assert result[0].name == sample_menu_data['name']
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_menus_with_filters(
        self, http_client_base_url, respx_mock, sample_menu_data
    ):
        respx_mock.get(f'{http_client_base_url}/menus/?name=test').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'Success',
                    'data': [sample_menu_data],
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.get_menus(name='test')
            assert isinstance(result, list)
            assert 'name=test' in str(respx_mock.calls.last.request.url)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_menus_api_error(self, http_client_base_url, respx_mock):
        respx_mock.get(f'{http_client_base_url}/menus/').mock(
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
            with pytest.raises(Exception, match='Erro ao buscar menus: Database error'):
                await client.get_menus()
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_menus_bad_response_format(
        self, http_client_base_url, respx_mock
    ):
        respx_mock.get(f'{http_client_base_url}/menus/').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'Success',
                    'data': {'id': 1},
                },
            )
        )

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            with pytest.raises(Exception, match='Resposta de menus mal formatada.'):
                await client.get_menus()
        finally:
            await client.close()


@pytest.mark.unit
class TestUpdateUser:
    """Testes para o método update_user."""

    @pytest.mark.asyncio
    async def test_update_user_success(self, http_client_base_url, respx_mock):
        respx_mock.patch(f'{http_client_base_url}/user').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'User updated',
                },
            )
        )

        user = User(data=UserData(name='João'), identity=UserIdentity())
        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            result = await client.update_user(user)
            assert result.status is True
            assert result.message == 'User updated'
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_update_user_api_error(
        self, http_client_base_url, respx_mock
    ):
        respx_mock.patch(f'{http_client_base_url}/user').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': False,
                    'message': 'Update failed',
                },
            )
        )

        user = User(data=UserData(name='João'), identity=UserIdentity())
        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            with pytest.raises(Exception, match='Erro ao atualizar usuário: Update failed'):
                await client.update_user(user)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_update_user_sends_correct_body(
        self, http_client_base_url, respx_mock
    ):
        respx_mock.patch(f'{http_client_base_url}/user').mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'User updated',
                },
            )
        )

        user = User(data=UserData(cpf='12345678900', name='João'), identity=UserIdentity())
        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            await client.update_user(user)
            import json
            body = json.loads(respx_mock.calls.last.request.content)
            assert body['data']['cpf'] == '12345678900'
        finally:
            await client.close()


@pytest.mark.unit
class TestTransferToMenu:
    """Testes para o método transfer_to_menu."""

    @pytest.mark.asyncio
    async def test_transfer_to_menu_without_route_does_not_include_route_in_payload(
        self, http_client_base_url, respx_mock, sample_chat_id_data
    ):
        """Testa que route='' não inclui chave 'route' no payload."""
        respx_mock.post(
            f'{http_client_base_url}/messages/transfer_to_menu'
        ).mock(
            return_value=httpx.Response(
                200,
                json={'status': True, 'message': 'Transferred'},
            )
        )

        from chatgraph.models.message import Message
        from chatgraph.models.userstate import ChatID, Menu

        chat_id = ChatID.from_dict(sample_chat_id_data)
        menu = Menu.from_name('main_menu')
        message = Message(text_message='olá')

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            await client.transfer_to_menu(chat_id, menu, message)
            import json
            body = json.loads(respx_mock.calls.last.request.content)
            assert 'route' not in body
            assert body['menu_id'] == 'main_menu'
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_transfer_to_menu_with_route_includes_route_in_payload(
        self, http_client_base_url, respx_mock, sample_chat_id_data
    ):
        """Testa que route='start.choice' inclui 'route' no payload."""
        respx_mock.post(
            f'{http_client_base_url}/messages/transfer_to_menu'
        ).mock(
            return_value=httpx.Response(
                200,
                json={'status': True, 'message': 'Transferred'},
            )
        )

        from chatgraph.models.message import Message
        from chatgraph.models.userstate import ChatID, Menu

        chat_id = ChatID.from_dict(sample_chat_id_data)
        menu = Menu.from_name('main_menu')
        message = Message(text_message='olá')

        client = RouterHTTPClient(base_url=http_client_base_url)

        try:
            await client.transfer_to_menu(chat_id, menu, message, route='start.choice')
            import json
            body = json.loads(respx_mock.calls.last.request.content)
            assert body['route'] == 'start.choice'
            assert body['menu_id'] == 'main_menu'
        finally:
            await client.close()


@pytest.mark.unit
class TestAssociateCpf:
    """Testes para o método associate_cpf."""

    def test_id_positiva_client_uses_correct_base(self, http_client_base_url):
        """Testa que _id_positiva_client aponta para /v1/id-positiva/."""
        client = RouterHTTPClient(base_url=http_client_base_url)
        assert str(client._id_positiva_client.base_url) == 'http://localhost:8080/v1/id-positiva/'

    def test_url_normalization_strips_actions(self):
        """Testa que ROUTER_URL sem /actions gera a mesma estrutura."""
        client_with = RouterHTTPClient(base_url='http://localhost:8080/v1/actions')
        client_without = RouterHTTPClient(base_url='http://localhost:8080/v1/')
        assert str(client_with._actions_client.base_url) == str(client_without._actions_client.base_url)
        assert str(client_with._id_positiva_client.base_url) == str(client_without._id_positiva_client.base_url)

    @pytest.mark.asyncio
    async def test_associate_cpf_uses_host_url_not_base_url(
        self, http_client_base_url, respx_mock, sample_chat_id_data
    ):
        """Garante que a URL usada é /v1/id-positiva/associate-cpf (host raiz),
        não /v1/actions/v1/id-positiva/associate-cpf."""
        expected_url = 'http://localhost:8080/v1/id-positiva/associate-cpf'
        respx_mock.post(expected_url).mock(
            return_value=httpx.Response(
                200, json={'status': True, 'message': 'CPF associado'}
            )
        )
        chat_id = ChatID.from_dict(sample_chat_id_data)
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            await client.associate_cpf(chat_id, cpf='12345678900', source='chatbot')
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_associate_cpf_raises_on_failure(
        self, http_client_base_url, respx_mock, sample_chat_id_data
    ):
        """Testa que status=False lança Exception com mensagem correta."""
        expected_url = 'http://localhost:8080/v1/id-positiva/associate-cpf'
        respx_mock.post(expected_url).mock(
            return_value=httpx.Response(
                200, json={'status': False, 'message': 'CPF inválido'}
            )
        )
        chat_id = ChatID.from_dict(sample_chat_id_data)
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            with pytest.raises(Exception, match='Erro ao associar CPF: CPF inválido'):
                await client.associate_cpf(chat_id, cpf='00000000000', source='chatbot')
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_associate_cpf_sends_bearer_token(
        self, http_client_config, respx_mock, sample_chat_id_data
    ):
        """Testa que o header Authorization usa Bearer token."""
        expected_url = 'http://localhost:8080/v1/id-positiva/associate-cpf'
        respx_mock.post(expected_url).mock(
            return_value=httpx.Response(
                200, json={'status': True, 'message': 'ok'}
            )
        )
        chat_id = ChatID.from_dict(sample_chat_id_data)
        client = RouterHTTPClient(
            base_url=http_client_config['base_url'],
            username=http_client_config['username'],
            password=http_client_config['password'],
        )
        try:
            await client.associate_cpf(chat_id, cpf='12345678900', source='chatbot')
            auth_header = respx_mock.calls.last.request.headers.get('Authorization', '')
            assert auth_header.startswith('Bearer ')
        finally:
            await client.close()


@pytest.mark.unit
class TestGetIdentity:
    """Testes para o método get_identity."""

    @pytest.mark.asyncio
    async def test_get_identity_returns_user_identity(
        self, http_client_base_url, respx_mock
    ):
        """Testa que get_identity retorna UserIdentity corretamente."""
        expected_url = 'http://localhost:8080/v1/id-positiva/identity'
        respx_mock.get(expected_url).mock(
            return_value=httpx.Response(
                200,
                json={
                    'status': True,
                    'message': 'ok',
                    'data': {
                        'cpf': '12345678900',
                        'auth_level': 'read',
                        'active': True,
                    },
                },
            )
        )
        from chatgraph.models.userstate import UserIdentity
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            result = await client.get_identity(user_id='user123')
            assert isinstance(result, UserIdentity)
            assert result.cpf == '12345678900'
            assert result.active is True
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_identity_sends_user_id_param(
        self, http_client_base_url, respx_mock
    ):
        """Testa que user_id é enviado como query param."""
        expected_url = 'http://localhost:8080/v1/id-positiva/identity'
        respx_mock.get(expected_url).mock(
            return_value=httpx.Response(
                200,
                json={'status': True, 'message': 'ok', 'data': {'auth_level': 'unknown'}},
            )
        )
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            await client.get_identity(user_id='user123')
            assert 'user_id=user123' in str(respx_mock.calls.last.request.url)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_identity_with_cpf_sends_cpf_param(
        self, http_client_base_url, respx_mock
    ):
        """Testa que cpf opcional é enviado quando fornecido."""
        expected_url = 'http://localhost:8080/v1/id-positiva/identity'
        respx_mock.get(expected_url).mock(
            return_value=httpx.Response(
                200,
                json={'status': True, 'message': 'ok', 'data': {'auth_level': 'unknown'}},
            )
        )
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            await client.get_identity(user_id='user123', cpf='12345678900')
            url_str = str(respx_mock.calls.last.request.url)
            assert 'user_id=user123' in url_str
            assert 'cpf=12345678900' in url_str
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_identity_raises_on_failure(
        self, http_client_base_url, respx_mock
    ):
        """Testa que status=False lança Exception com mensagem correta."""
        expected_url = 'http://localhost:8080/v1/id-positiva/identity'
        respx_mock.get(expected_url).mock(
            return_value=httpx.Response(
                200,
                json={'status': False, 'message': 'Usuário não encontrado'},
            )
        )
        client = RouterHTTPClient(base_url=http_client_base_url)
        try:
            with pytest.raises(Exception, match='Erro ao consultar identidade: Usuário não encontrado'):
                await client.get_identity(user_id='user_inexistente')
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_get_identity_uses_bearer_auth(
        self, http_client_config, respx_mock
    ):
        """Testa que o header Authorization usa Bearer token."""
        expected_url = 'http://localhost:8080/v1/id-positiva/identity'
        respx_mock.get(expected_url).mock(
            return_value=httpx.Response(
                200,
                json={'status': True, 'message': 'ok', 'data': {'auth_level': 'unknown'}},
            )
        )
        client = RouterHTTPClient(
            base_url=http_client_config['base_url'],
            username=http_client_config['username'],
            password=http_client_config['password'],
        )
        try:
            await client.get_identity(user_id='user123')
            auth_header = respx_mock.calls.last.request.headers.get('Authorization', '')
            assert auth_header.startswith('Bearer ')
        finally:
            await client.close()
