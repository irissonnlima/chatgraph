"""
Testes para a classe UserCall.
"""

from unittest.mock import MagicMock

import pytest

from chatgraph.models.message import Message
from chatgraph.models.userstate import (
    AuthLevel,
    ChatID,
    Menu,
    User,
    UserData,
    UserIdentity,
    UserState,
)
from chatgraph.types.usercall import UserCall


@pytest.fixture
def sample_user():
    return User(
        data=UserData(name='João Silva', cpf='12345678900'),
        identity=UserIdentity(auth_level=AuthLevel.READ),
    )


@pytest.fixture
def sample_user_state(sample_user):
    return UserState(
        chat_id=ChatID(user_id='user123', company_id='company456'),
        platform='whatsapp',
        session_id=1,
        menu=Menu(name='Suporte'),
        user=sample_user,
        route='start',
    )


@pytest.fixture
def sample_message():
    return Message('Olá')


@pytest.fixture
def mock_router_client():
    return MagicMock()


@pytest.fixture
def user_call(sample_user_state, sample_message, mock_router_client):
    return UserCall(
        user_state=sample_user_state,
        message=sample_message,
        router_client=mock_router_client,
    )


@pytest.mark.unit
class TestUserCallUserProperty:
    """Testes para a property user de UserCall."""

    def test_user_returns_user_object(self, user_call, sample_user):
        """call.user retorna o objeto User correto do UserState."""
        assert user_call.user is sample_user

    def test_user_data_name(self, user_call):
        """call.user.data.name acessa o nome corretamente."""
        assert user_call.user.data.name == 'João Silva'

    def test_user_identity_auth_level(self, user_call):
        """call.user.identity.auth_level retorna o nível correto."""
        assert user_call.user.identity.auth_level == AuthLevel.READ
