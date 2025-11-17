"""
Configuração de fixtures para testes de integração.

Este módulo contém fixtures para testes de integração que fazem
chamadas reais para APIs externas.
"""

import os
from dotenv import load_dotenv

import pytest
import pytest_asyncio

from chatgraph.services.router_http_client import RouterHTTPClient

load_dotenv()  # Carrega variáveis de ambiente do arquivo .env


def pytest_configure(config):
    """Registra markers customizados."""
    config.addinivalue_line(
        'markers', 'integration: mark test as integration test'
    )


def pytest_collection_modifyitems(config, items):
    """Adiciona marker 'integration' automaticamente para testes neste diretório."""
    for item in items:
        if 'integration' in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def skip_if_no_integration_env():
    """Skip test se variáveis de ambiente de integração não estiverem configuradas."""
    required_vars = ['ROUTER_API_BASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        pytest.skip(
            f'Variáveis de ambiente não configuradas: {", ".join(missing_vars)}. '
            'Configure as variáveis para executar testes de integração.'
        )


@pytest.fixture
def integration_base_url(skip_if_no_integration_env):
    """URL base real da API para testes de integração."""
    return os.getenv('ROUTER_API_BASE_URL')


@pytest.fixture
def integration_username():
    """Username para autenticação na API (opcional)."""
    return os.getenv('ROUTER_API_USERNAME')


@pytest.fixture
def integration_password():
    """Password para autenticação na API (opcional)."""
    return os.getenv('ROUTER_API_PASSWORD')


@pytest.fixture
def integration_timeout():
    """Timeout para requisições de integração (default: 60s)."""
    return float(os.getenv('ROUTER_API_TIMEOUT', '60.0'))


@pytest_asyncio.fixture
async def real_http_client(
    integration_base_url,
    integration_username,
    integration_password,
    integration_timeout,
):
    """
    Cliente HTTP real para testes de integração.

    Este fixture cria um RouterHTTPClient configurado com as credenciais
    reais da API, permitindo testar a integração completa.
    """
    client = RouterHTTPClient(
        base_url=integration_base_url,
        username=integration_username,
        password=integration_password,
        timeout=integration_timeout,
    )

    yield client

    # Cleanup: fecha o cliente após o teste
    await client.close()


@pytest.fixture
def sample_test_user_id():
    """ID de usuário para testes de integração."""
    return os.getenv('TEST_USER_ID', 'test_user_001')


@pytest.fixture
def sample_test_company_id():
    """ID de empresa para testes de integração."""
    return os.getenv('TEST_COMPANY_ID', 'test_company_001')


@pytest.fixture
def sample_test_file_id():
    """ID de arquivo para testes de integração."""
    return '2e336e9f9880e5b429071d88edff6cf51f613ffa44eed545ce92b81e5447770c'
