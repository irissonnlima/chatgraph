"""
Configuração de fixtures para os testes.

Este módulo contém fixtures compartilhadas entre todos os testes.
"""

import pytest
import respx


@pytest.fixture
def respx_mock():
    """Fixture que fornece um respx mock para testes HTTP."""
    with respx.mock:
        yield respx


# Fixtures para RouterHTTPClient
@pytest.fixture
def http_client_base_url():
    """URL base padrão para testes do RouterHTTPClient."""
    return 'http://localhost:8080/v1/actions'


@pytest.fixture
def http_client_credentials():
    """Credenciais padrão para testes do RouterHTTPClient."""
    return {
        'username': 'testuser',
        'password': 'f078b1cf-b4c8-11f0-b4fe-0242ac140002',
    }


@pytest.fixture
def http_client_config(http_client_base_url, http_client_credentials):
    """Configuração completa para RouterHTTPClient."""
    return {
        'base_url': http_client_base_url,
        'username': http_client_credentials['username'],
        'password': http_client_credentials['password'],
        'timeout': 30.0,
    }


@pytest.fixture
def sample_chat_id_data():
    """Fixture com dados de exemplo para ChatID."""
    return {'user_id': 'user123', 'company_id': 'company456'}


@pytest.fixture
def sample_user_data():
    """Fixture com dados de exemplo para User."""
    return {
        'cpf': '12345678900',
        'name': 'João Silva',
        'phone': '11999999999',
        'email': 'joao@example.com',
    }


@pytest.fixture
def sample_menu_data():
    """Fixture com dados de exemplo para Menu."""
    return {
        'id': 1,
        'department_id': 10,
        'name': 'Suporte',
        'description': 'Menu de suporte',
        'active': True,
    }


@pytest.fixture
def sample_file_data():
    """Fixture com dados de exemplo para File."""
    return {
        'id': 'file123',
        'send_type': 'IMAGE',
        'url': 'https://example.com/image.jpg',
        'name': 'image.jpg',
        'mime_type': 'image/jpeg',
        'size': 1024,
    }


@pytest.fixture
def sample_button_data():
    """Fixture com dados de exemplo para Button."""
    return {'type': 'postback', 'title': 'Sim', 'detail': 'confirm_yes'}


@pytest.fixture
def sample_message_data():
    """Fixture com dados de exemplo para Message."""
    return {
        'text_message': {'title': 'Olá', 'detail': 'Bem-vindo'},
        'buttons': [{'type': 'postback', 'title': 'Sim'}],
        'date_time': '2025-11-14T10:00:00',
    }


@pytest.fixture
def sample_user_state_data(sample_chat_id_data):
    """Fixture com dados de exemplo para UserState."""
    return {
        'chat_id': sample_chat_id_data,
        'platform': 'whatsapp',
        'session_id': 100,
        'menu': {'name': 'Main'},
        'user': {'name': 'João Silva'},
        'route': 'start',
        'observation': 'test observation',
    }
