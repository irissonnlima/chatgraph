"""
Testes para os modelos de UserState.

Este módulo contém testes unitários para ChatID, User, Menu e UserState.
"""

import pytest
from chatgraph.models.userstate import (
    ChatID,
    User,
    Menu,
    UserState,
    AuthLevel,
    UserData,
    UserIdentity,
    UserInternal,
)


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

    def test_chatid_str(self):
        """Testa representação string de ChatID."""
        chat_id = ChatID(user_id='user123', company_id='company456')
        assert str(chat_id) == 'user123:company456'


@pytest.mark.unit
class TestAuthLevel:
    """Testes para o enum AuthLevel."""

    def test_authlevel_from_value_string(self):
        assert AuthLevel.from_value('read') == AuthLevel.READ
        assert AuthLevel.from_value('write') == AuthLevel.WRITE
        assert AuthLevel.from_value('blocked') == AuthLevel.BLOCKED
        assert AuthLevel.from_value('unknown') == AuthLevel.UNKNOWN

    def test_authlevel_from_value_string_case_insensitive(self):
        assert AuthLevel.from_value('READ') == AuthLevel.READ
        assert AuthLevel.from_value('Write') == AuthLevel.WRITE

    def test_authlevel_from_value_string_invalid(self):
        assert AuthLevel.from_value('invalid') == AuthLevel.UNKNOWN

    def test_authlevel_from_value_int(self):
        assert AuthLevel.from_value(-1) == AuthLevel.BLOCKED
        assert AuthLevel.from_value(0) == AuthLevel.UNKNOWN
        assert AuthLevel.from_value(1) == AuthLevel.READ
        assert AuthLevel.from_value(2) == AuthLevel.WRITE

    def test_authlevel_from_value_int_invalid(self):
        assert AuthLevel.from_value(99) == AuthLevel.UNKNOWN

    def test_authlevel_from_value_none(self):
        assert AuthLevel.from_value(None) == AuthLevel.UNKNOWN

    def test_authlevel_ordering_unknown_lt_read(self):
        assert AuthLevel.UNKNOWN < AuthLevel.READ

    def test_authlevel_ordering_read_lt_write(self):
        assert AuthLevel.READ < AuthLevel.WRITE

    def test_authlevel_ordering_blocked_lt_unknown(self):
        assert AuthLevel.BLOCKED < AuthLevel.UNKNOWN

    def test_authlevel_ordering_write_gt_read(self):
        assert AuthLevel.WRITE > AuthLevel.READ

    def test_authlevel_ordering_read_eq_read(self):
        assert AuthLevel.READ == AuthLevel.READ

    def test_authlevel_ordering_write_ge_write(self):
        assert AuthLevel.WRITE >= AuthLevel.WRITE


@pytest.mark.unit
class TestUserData:
    """Testes para a classe UserData."""

    def test_userdata_initialization_defaults(self):
        user_data = UserData()
        assert user_data.cpf is None
        assert user_data.name is None
        assert user_data.phone is None
        assert user_data.email is None
        assert user_data.profile_photo_url is None
        assert user_data.nickname is None

    def test_userdata_to_dict_omits_none(self):
        user_data = UserData(name='João Silva', cpf='12345678900')
        result = user_data.to_dict()
        assert result == {'name': 'João Silva', 'cpf': '12345678900'}
        assert 'phone' not in result
        assert 'email' not in result

    def test_userdata_to_dict_all_fields(self):
        user_data = UserData(
            cpf='12345678900',
            name='João',
            phone='11999999999',
            email='joao@example.com',
            profile_photo_url='https://example.com/photo.jpg',
            nickname='joaozinho',
        )
        result = user_data.to_dict()
        assert result['cpf'] == '12345678900'
        assert result['profile_photo_url'] == 'https://example.com/photo.jpg'
        assert result['nickname'] == 'joaozinho'

    def test_userdata_from_dict(self):
        data = {
            'cpf': '12345678900',
            'name': 'João Silva',
            'phone': '11999999999',
            'email': 'joao@example.com',
            'profile_photo_url': 'https://example.com/photo.jpg',
            'nickname': 'joaozinho',
        }
        user_data = UserData.from_dict(data)
        assert user_data.cpf == '12345678900'
        assert user_data.name == 'João Silva'
        assert user_data.profile_photo_url == 'https://example.com/photo.jpg'
        assert user_data.nickname == 'joaozinho'

    def test_userdata_from_dict_empty(self):
        user_data = UserData.from_dict({})
        assert user_data.cpf is None
        assert user_data.name is None


@pytest.mark.unit
class TestUserIdentity:
    """Testes para a classe UserIdentity."""

    def test_useridentity_initialization_defaults(self):
        identity = UserIdentity()
        assert identity.cpf is None
        assert identity.auth_level == AuthLevel.UNKNOWN
        assert identity.active is None

    def test_useridentity_to_dict_includes_auth_level(self):
        identity = UserIdentity(auth_level=AuthLevel.READ)
        result = identity.to_dict()
        assert result['auth_level'] == 'read'

    def test_useridentity_to_dict_omits_none(self):
        identity = UserIdentity(auth_level=AuthLevel.WRITE, auth_status='ok')
        result = identity.to_dict()
        assert result['auth_level'] == 'write'
        assert result['auth_status'] == 'ok'
        assert 'cpf' not in result
        assert 'device_id' not in result

    def test_useridentity_from_dict(self):
        data = {
            'cpf': '12345678900',
            'auth_level': 'read',
            'auth_status': 'active',
            'last_access_at': '2025-01-01T00:00:00',
        }
        identity = UserIdentity.from_dict(data)
        assert identity.cpf == '12345678900'
        assert identity.auth_level == AuthLevel.READ
        assert identity.auth_status == 'active'
        assert identity.last_access_at == '2025-01-01T00:00:00'

    def test_useridentity_from_dict_int_auth_level(self):
        identity = UserIdentity.from_dict({'auth_level': 2})
        assert identity.auth_level == AuthLevel.WRITE

    def test_useridentity_from_dict_empty(self):
        identity = UserIdentity.from_dict({})
        assert identity.auth_level == AuthLevel.UNKNOWN


@pytest.mark.unit
class TestUserInternal:
    """Testes para a classe UserInternal."""

    def test_userinternal_initialization_defaults(self):
        internal = UserInternal()
        assert internal.matricula is None
        assert internal.cargo is None
        assert internal.filial is None
        assert internal.empresa is None
        assert internal.data_admissao is None

    def test_userinternal_to_dict_omits_none(self):
        internal = UserInternal(matricula='12345', cargo='Analista')
        result = internal.to_dict()
        assert result == {'matricula': '12345', 'cargo': 'Analista'}
        assert 'filial' not in result

    def test_userinternal_from_dict(self):
        data = {
            'matricula': '12345',
            'cargo': 'Analista',
            'filial': 'SP',
            'empresa': 'ACME',
            'data_admissao': '2020-01-01',
        }
        internal = UserInternal.from_dict(data)
        assert internal.matricula == '12345'
        assert internal.cargo == 'Analista'
        assert internal.filial == 'SP'
        assert internal.empresa == 'ACME'
        assert internal.data_admissao == '2020-01-01'

    def test_userinternal_from_dict_empty(self):
        internal = UserInternal.from_dict({})
        assert internal.matricula is None


@pytest.mark.unit
class TestUser:
    """Testes para a classe User (estrutura aninhada)."""

    def test_user_initialization_defaults(self):
        user = User()
        assert isinstance(user.data, UserData)
        assert isinstance(user.identity, UserIdentity)
        assert user.internal is None

    def test_user_initialization_with_data(self):
        user = User(
            data=UserData(
                cpf='12345678900',
                name='João Silva',
                phone='11999999999',
                email='joao@example.com',
            ),
            identity=UserIdentity(auth_level=AuthLevel.READ),
        )
        assert user.data.cpf == '12345678900'
        assert user.data.name == 'João Silva'
        assert user.data.phone == '11999999999'
        assert user.data.email == 'joao@example.com'
        assert user.identity.auth_level == AuthLevel.READ

    def test_user_to_dict(self):
        user = User(
            data=UserData(name='João'),
            identity=UserIdentity(auth_level=AuthLevel.WRITE),
        )
        result = user.to_dict()
        assert 'data' in result
        assert 'identity' in result
        assert result['data']['name'] == 'João'
        assert result['identity']['auth_level'] == 'write'
        assert 'internal' not in result

    def test_user_to_dict_with_internal(self):
        user = User(
            data=UserData(name='João'),
            identity=UserIdentity(),
            internal=UserInternal(matricula='12345'),
        )
        result = user.to_dict()
        assert 'internal' in result
        assert result['internal']['matricula'] == '12345'

    def test_user_from_dict_nested(self):
        data = {
            'data': {'cpf': '12345678900', 'name': 'João'},
            'identity': {'auth_level': 'read'},
            'internal': None,
        }
        user = User.from_dict(data)
        assert user.data.cpf == '12345678900'
        assert user.data.name == 'João'
        assert user.identity.auth_level == AuthLevel.READ
        assert user.internal is None

    def test_user_from_dict_with_internal(self):
        data = {
            'data': {},
            'identity': {},
            'internal': {'matricula': '99999', 'cargo': 'Gerente'},
        }
        user = User.from_dict(data)
        assert user.internal is not None
        assert user.internal.matricula == '99999'
        assert user.internal.cargo == 'Gerente'

    def test_user_from_dict_empty(self):
        user = User.from_dict({})
        assert isinstance(user.data, UserData)
        assert isinstance(user.identity, UserIdentity)
        assert user.internal is None

    def test_user_from_dict_with_empty_internal(self):
        data = {'data': {}, 'identity': {}, 'internal': {}}
        user = User.from_dict(data)
        assert user.internal is None


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

    def test_menu_to_dict_with_protection_level(self):
        menu = Menu(name='Privado', protection_level=AuthLevel.READ)
        result = menu.to_dict()
        assert result['protection_level'] == 'read'

    def test_menu_to_dict_without_protection_level(self):
        menu = Menu(name='Público')
        result = menu.to_dict()
        assert 'protection_level' not in result

    def test_menu_from_dict_with_protection_level(self):
        data = {'name': 'Privado', 'protection_level': 'write'}
        menu = Menu.from_dict(data)
        assert menu.protection_level == AuthLevel.WRITE

    def test_menu_from_dict_without_protection_level(self):
        data = {'name': 'Público'}
        menu = Menu.from_dict(data)
        assert menu.protection_level is None

    def test_menu_from_dict_with_int_protection_level(self):
        data = {'protection_level': 1}
        menu = Menu.from_dict(data)
        assert menu.protection_level == AuthLevel.READ


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
        user = User(data=UserData(name='João'))
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
            'user': {'data': {'name': 'João'}, 'identity': {}},
            'route': 'start',
        }
        user_state = UserState.from_dict(data)

        assert user_state.chat_id.user_id == 'user123'
        assert user_state.platform == 'whatsapp'
        assert user_state.session_id == 100
        assert user_state.menu.name == 'Main' if user_state.menu.name else ''
        assert user_state.user.data.name == 'João'
        assert user_state.route == 'start'
