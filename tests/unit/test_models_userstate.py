"""
Testes para os modelos de UserState.

Este módulo contém testes unitários para ChatID, User, Menu e UserState.
"""

import pytest
from chatgraph.models.userstate import ChatID, User, Menu, UserState


@pytest.mark.unit
class TestChatID:
    """Testes para a classe ChatID."""

    def test_chatid_initialization(self):
        """Testa inicialização básica do ChatID."""
        chat_id = ChatID(user_id='user123', company_id='company456')

        assert chat_id.user_id == 'user123'
        assert chat_id.company_id == 'company456'

    def test_chatid_to_dict(self):
        """Testa conversão de ChatID para dicionário."""
        chat_id = ChatID(user_id='user123', company_id='company456')
        result = chat_id.to_dict()

        assert result == {
            'user_id': 'user123',
            'company_id': 'company456',
        }

    def test_chatid_from_dict(self):
        """Testa criação de ChatID a partir de dicionário."""
        data = {'user_id': 'user123', 'company_id': 'company456'}
        chat_id = ChatID.from_dict(data)

        assert chat_id.user_id == 'user123'
        assert chat_id.company_id == 'company456'

    def test_chatid_from_dict_with_missing_fields(self):
        """Testa criação de ChatID com campos faltando."""
        data = {}
        chat_id = ChatID.from_dict(data)

        assert chat_id.user_id == ''
        assert chat_id.company_id == ''


@pytest.mark.unit
class TestUser:
    """Testes para a classe User."""

    def test_user_initialization_with_all_fields(self):
        """Testa inicialização do User com todos os campos."""
        user = User(
            cpf='12345678900',
            name='João Silva',
            phone='11999999999',
            email='joao@example.com',
        )

        assert user.cpf == '12345678900'
        assert user.name == 'João Silva'
        assert user.phone == '11999999999'
        assert user.email == 'joao@example.com'

    def test_user_initialization_with_defaults(self):
        """Testa inicialização do User com valores padrão."""
        user = User()

        assert user.cpf is None
        assert user.name is None
        assert user.phone is None
        assert user.email is None

    def test_user_to_dict_with_all_fields(self):
        """Testa conversão para dicionário com todos os campos."""
        user = User(
            cpf='12345678900',
            name='João Silva',
            phone='11999999999',
            email='joao@example.com',
        )
        result = user.to_dict()

        assert result == {
            'cpf': '12345678900',
            'name': 'João Silva',
            'phone': '11999999999',
            'email': 'joao@example.com',
        }

    def test_user_to_dict_omits_none_fields(self):
        """Testa que to_dict omite campos None."""
        user = User(name='João Silva')
        result = user.to_dict()

        assert result == {'name': 'João Silva'}
        assert 'cpf' not in result
        assert 'phone' not in result
        assert 'email' not in result

    def test_user_from_dict(self):
        """Testa criação de User a partir de dicionário."""
        data = {
            'cpf': '12345678900',
            'name': 'João Silva',
            'phone': '11999999999',
            'email': 'joao@example.com',
        }
        user = User.from_dict(data)

        assert user.cpf == '12345678900'
        assert user.name == 'João Silva'
        assert user.phone == '11999999999'
        assert user.email == 'joao@example.com'


@pytest.mark.unit
class TestMenu:
    """Testes para a classe Menu."""

    def test_menu_initialization_with_all_fields(self):
        """Testa inicialização do Menu com todos os campos."""
        menu = Menu(
            id=1,
            department_id=10,
            name='Suporte',
            description='Menu de suporte',
            active=True,
        )

        assert menu.id == 1
        assert menu.department_id == 10
        assert menu.name == 'Suporte'
        assert menu.description == 'Menu de suporte'
        assert menu.active is True

    def test_menu_initialization_with_defaults(self):
        """Testa inicialização do Menu com valores padrão."""
        menu = Menu()

        assert menu.id is None
        assert menu.department_id is None
        assert menu.name is None
        assert menu.description is None
        assert menu.active is None

    def test_menu_to_dict_with_all_fields(self):
        """Testa conversão para dicionário com todos os campos."""
        menu = Menu(
            id=1,
            department_id=10,
            name='Suporte',
            description='Menu de suporte',
            active=True,
        )
        result = menu.to_dict()

        assert result == {
            'id': 1,
            'department_id': 10,
            'name': 'Suporte',
            'description': 'Menu de suporte',
            'active': True,
        }

    def test_menu_to_dict_omits_none_fields(self):
        """Testa que to_dict omite campos None."""
        menu = Menu(name='Suporte')
        result = menu.to_dict()

        assert result == {'name': 'Suporte'}
        assert 'id' not in result

    def test_menu_from_dict(self):
        """Testa criação de Menu a partir de dicionário."""
        data = {
            'id': 1,
            'department_id': 10,
            'name': 'Suporte',
            'description': 'Menu de suporte',
            'active': True,
        }
        menu = Menu.from_dict(data)

        assert menu.id == 1
        assert menu.department_id == 10
        assert menu.name == 'Suporte'


@pytest.mark.unit
class TestUserState:
    """Testes para a classe UserState."""

    def test_userstate_initialization(self):
        """Testa inicialização básica do UserState."""
        chat_id = ChatID(user_id='user123', company_id='company456')
        user_state = UserState(chat_id=chat_id, platform='whatsapp')

        assert user_state.chat_id == chat_id
        assert user_state.platform == 'whatsapp'
        assert user_state.session_id is None
        assert isinstance(user_state.menu, Menu)
        assert isinstance(user_state.user, User)

    def test_userstate_to_dict(self):
        """Testa conversão de UserState para dicionário."""
        chat_id = ChatID(user_id='user123', company_id='company456')
        menu = Menu(name='Main')
        user = User(name='João')
        user_state = UserState(
            chat_id=chat_id,
            platform='whatsapp',
            session_id=100,
            menu=menu,
            user=user,
            route='start',
            observation='test',
        )
        result = user_state.to_dict()

        assert result['chat_id'] == {
            'user_id': 'user123',
            'company_id': 'company456',
        }
        assert result['platform'] == 'whatsapp'
        assert result['session_id'] == 100
        assert result['route'] == 'start'
        assert result['observation'] == 'test'

    def test_userstate_from_dict(self):
        """Testa criação de UserState a partir de dicionário."""
        data = {
            'chat_id': {'user_id': 'user123', 'company_id': 'company456'},
            'platform': 'whatsapp',
            'session_id': 100,
            'menu': {'name': 'Main'},
            'user': {'name': 'João'},
            'route': 'start',
        }
        user_state = UserState.from_dict(data)

        assert user_state.chat_id.user_id == 'user123'
        assert user_state.platform == 'whatsapp'
        assert user_state.session_id == 100
        assert user_state.menu.name == 'Main' if user_state.menu.name else ''
        assert user_state.user.name == 'João' if user_state.user.name else ''
        assert user_state.route == 'start'
