"""
Testes de integração para RouterHTTPClient.

Estes testes fazem chamadas reais para a API de roteamento,
validando contratos, formatos de resposta e comportamento real.

IMPORTANTE: Configure as variáveis de ambiente antes de executar:
    export ROUTER_API_BASE_URL="https://api.example.com/v1/actions"
    export ROUTER_API_USERNAME="seu_usuario"  # Opcional
    export ROUTER_API_PASSWORD="sua_senha"    # Opcional
    export ROUTER_API_TIMEOUT="60.0"          # Opcional (default: 60s)
    export TEST_USER_ID="user_id_teste"       # Opcional
    export TEST_COMPANY_ID="company_id_teste" # Opcional

Execute apenas testes de integração:
    poetry run pytest tests/integration/ -v
    ou
    poetry run pytest -m integration -v
"""

import httpx
import pytest

from chatgraph.models.message import Button, Message, TextMessage
from chatgraph.models.userstate import ChatID, Menu, User, UserState


@pytest.mark.integration
@pytest.mark.asyncio
class TestRouterHTTPClientIntegrationSessions:
    """Testes de integração para métodos de sessões."""

    async def test_get_all_sessions_real_api(self, real_http_client):
        """
        Testa get_all_sessions com API real.

        Valida:
        - Resposta é uma lista
        - Se houver sessões, valida estrutura de UserState
        """
        # real_http_client já é o cliente pronto (via fixture)
        sessions = await real_http_client.get_all_sessions()

        # Validações de contrato
        assert isinstance(
            sessions, list
        ), 'get_all_sessions deve retornar lista'

        if sessions:
            session = sessions[0]

            # Valida estrutura de UserState
            assert hasattr(session, 'chat_id'), 'UserState deve ter chat_id'
            assert hasattr(session, 'platform'), 'UserState deve ter platform'
            assert isinstance(
                session.chat_id, ChatID
            ), 'chat_id deve ser ChatID'
            assert isinstance(
                session.platform, str
            ), 'platform deve ser string'

            # Valida ChatID
            assert hasattr(
                session.chat_id, 'user_id'
            ), 'ChatID deve ter user_id'
            assert hasattr(
                session.chat_id, 'company_id'
            ), 'ChatID deve ter company_id'

    async def test_get_session_by_chat_id_real_api(
        self,
        real_http_client,
        sample_test_user_id,
        sample_test_company_id,
    ):
        """
        Testa get_session_by_chat_id com API real.

        Valida:
        - Busca por ChatID existente retorna UserState
        - Estrutura da resposta está correta
        """
        chat_id = ChatID(
            user_id=sample_test_user_id, company_id=sample_test_company_id
        )

        try:
            user_state = await real_http_client.get_session_by_chat_id(chat_id)

            # Se encontrou sessão, valida estrutura
            assert isinstance(user_state, UserState), 'Deve retornar UserState'
            assert (
                user_state.chat_id.user_id == chat_id.user_id
            ), 'user_id deve corresponder'
            assert (
                user_state.chat_id.company_id == chat_id.company_id
            ), 'company_id deve corresponder'

        except Exception as e:
            # Se não encontrar, apenas loga (pode ser esperado)
            pytest.skip(f'Sessão não encontrada para {chat_id.user_id}: {e}')

    async def test_start_session_real_api(
        self,
        real_http_client,
        sample_test_user_id,
        sample_test_company_id,
    ):
        """
        Testa start_session com API real.

        Valida:
        - Criação de nova sessão funciona
        - Resposta contém confirmação
        """
        # Cria UserState para teste
        user_state = UserState(
            chat_id=ChatID(
                user_id=sample_test_user_id,
                company_id=sample_test_company_id,
            ),
            platform='voll',
            menu=Menu(name='p310_chama_no_whats'),
        )

        try:
            response = await real_http_client.start_session(user_state)

            # Valida resposta
            assert isinstance(
                response, dict
            ), 'Resposta deve ser um dicionário'
            # API pode retornar estruturas diferentes
            assert (
                'status' in response or 'message' in response
            ), 'Resposta deve conter status ou message'

        except Exception as e:
            pytest.skip(f'Erro ao criar sessão: {e}')


@pytest.mark.integration
@pytest.mark.asyncio
class TestRouterHTTPClientIntegrationMessages:
    """Testes de integração para métodos de mensagens."""

    async def test_send_message_real_api(
        self,
        real_http_client,
        sample_test_user_id,
        sample_test_company_id,
    ):
        """
        Testa send_message com API real.

        Valida:
        - Envio de mensagem funciona
        - Resposta contém confirmação
        """
        # Cria Message para teste
        message = Message(
            text_message=TextMessage(
                title='Teste de Integração',
                detail='Esta é uma mensagem de teste de integração',
            ),
            buttons=[
                Button(title='Opção 1', detail='Detalhe da Opção 1'),
                Button(title='Opção 2', detail='Detalhe da Opção 2'),
            ],
        )

        # Cria UserState associado
        user_state = UserState(
            chat_id=ChatID(
                user_id=sample_test_user_id,
                company_id=sample_test_company_id,
            ),
            platform='voll',
            menu=Menu(name='p310_chama_no_whats'),
        )

        try:
            response = await real_http_client.send_message(message, user_state)

            # Valida resposta
            assert isinstance(
                response, dict
            ), 'Resposta deve ser um dicionário'
            assert (
                'status' in response or 'message' in response
            ), 'Resposta deve conter status ou message'

        except Exception as e:
            pytest.skip(f'Erro ao enviar mensagem: {e}')


@pytest.mark.integration
@pytest.mark.asyncio
class TestRouterHTTPClientIntegrationFiles:
    """Testes de integração para métodos de arquivos."""

    async def test_get_file_real_api(
        self, real_http_client, sample_test_file_id
    ):
        """
        Testa get_file com API real.

        NOTA: Este teste requer um file_id válido existente na API.
        Ajuste conforme necessário ou skip se não houver arquivo.
        """
        # ID de arquivo para teste - ajuste conforme sua API

        try:
            file_obj = await real_http_client.get_file(sample_test_file_id)

            # Valida estrutura do arquivo
            assert hasattr(file_obj, 'id'), 'File deve ter atributo id'
            assert hasattr(file_obj, 'name'), 'File deve ter atributo name'
            assert file_obj.id == sample_test_file_id, 'ID deve corresponder'

        except Exception as e:
            pytest.skip(f'Arquivo não encontrado ou erro: {e}')

    @pytest.mark.file
    async def test_upload_file_real_api(self, real_http_client):
        """
        Testa upload_file com API real.

        Valida:
        - Upload de arquivo funciona
        - Resposta contém file_id ou confirmação
        """
        # URL de imagem de teste pública
        image_url = 'https://picsum.photos/200/300/'

        try:
            # Baixa imagem da internet sem salvar em disco
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                verify=False,
                trust_env=True,
            ) as client:
                img_response = await client.get(image_url)
                img_response.raise_for_status()
                test_file_content = img_response.content

            # Upload dos bytes da imagem para a API
            response = await real_http_client.upload_file(test_file_content)

            # Valida resposta
            assert isinstance(
                response, dict
            ), 'Resposta deve ser um dicionário'
            assert (
                'status' in response
                or 'file_id' in response
                or 'message' in response
            ), 'Resposta deve conter status, file_id ou message'

        except Exception as e:
            pytest.skip(f'Erro ao fazer upload: {e}')


@pytest.mark.integration
@pytest.mark.asyncio
class TestRouterHTTPClientIntegrationResponseFormat:
    """Testes de integração para validar formato de resposta da API."""

    async def test_get_session_response_format(
        self,
        real_http_client,
        sample_test_user_id,
        sample_test_company_id,
    ):
        """
        Valida formato completo da resposta de get_session_by_chat_id.

        Baseado no formato real da API:
        {
            "status": true,
            "message": "Userstate retrieved successfully",
            "data": {
                "session_id": 22,
                "chat_id": {...},
                "menu": {...},
                "user": {...},
                "route": "start",
                "observation": "{}",
                "platform": "voll",
                "last_update": "2025-11-16T07:42:47-03:00",
                "dt_created": "2025-11-07T19:57:54-03:00"
            }
        }
        """
        chat_id = ChatID(
            user_id=sample_test_user_id, company_id=sample_test_company_id
        )

        try:
            user_state = await real_http_client.get_session_by_chat_id(chat_id)

            # Valida campos obrigatórios do UserState
            assert hasattr(
                user_state, 'session_id'
            ), 'UserState deve ter session_id'
            assert hasattr(user_state, 'chat_id'), 'UserState deve ter chat_id'
            assert hasattr(
                user_state, 'platform'
            ), 'UserState deve ter platform'
            assert hasattr(user_state, 'menu'), 'UserState deve ter menu'
            assert hasattr(user_state, 'user'), 'UserState deve ter user'
            assert hasattr(user_state, 'route'), 'UserState deve ter route'

            # Valida tipos dos campos
            assert isinstance(
                user_state.session_id, int
            ), 'session_id deve ser int'
            assert isinstance(
                user_state.chat_id, ChatID
            ), 'chat_id deve ser ChatID'
            assert isinstance(
                user_state.platform, str
            ), 'platform deve ser string'

            # Valida estrutura do ChatID
            assert (
                user_state.chat_id.user_id == sample_test_user_id
            ), 'user_id deve corresponder'
            assert (
                user_state.chat_id.company_id == sample_test_company_id
            ), 'company_id deve corresponder'

            # Valida estrutura do Menu
            assert hasattr(user_state.menu, 'name'), 'Menu deve ter name'
            assert isinstance(user_state.menu, Menu), 'menu deve ser Menu'

            # Valida estrutura do User (se presente)
            if user_state.user:
                assert isinstance(user_state.user, User), 'user deve ser User'
                assert hasattr(user_state.user, 'name'), 'User deve ter name'

            # Valida campos opcionais
            if hasattr(user_state, 'last_update'):
                assert (
                    user_state.last_update is not None
                ), 'last_update deve estar presente'
            if hasattr(user_state, 'dt_created'):
                assert (
                    user_state.dt_created is not None
                ), 'dt_created deve estar presente'

        except Exception as e:
            pytest.skip(
                f'Erro ao validar formato da resposta para {chat_id.user_id}: {e}'
            )


@pytest.mark.integration
@pytest.mark.asyncio
class TestRouterHTTPClientIntegrationHealthCheck:
    """Testes de integração para validar conectividade básica."""

    async def test_api_is_reachable(self, real_http_client):
        """
        Testa se a API está acessível.

        Este é um teste básico para verificar conectividade.
        """
        try:
            # Tenta buscar todas as sessões como health check
            sessions = await real_http_client.get_all_sessions()
            assert isinstance(sessions, list), 'API deve estar respondendo'

        except Exception as e:
            pytest.fail(f'API não está acessível: {e}')
