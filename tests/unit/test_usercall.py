"""
Testes para a classe UserCall.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatgraph.models.message import Message
from chatgraph.models.platform_state import PlatformState
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


@pytest.mark.unit
class TestAddObservation:
    """Testes para o método add_observation de UserCall."""

    @pytest.fixture
    def user_call_with_menu(self, sample_message, mock_router_client):
        user = User(
            data=UserData(name='João Silva', cpf='11111111111'),
            identity=UserIdentity(
                auth_level=AuthLevel.READ, cpf='11111111111'
            ),
        )
        user_state = UserState(
            chat_id=ChatID(user_id='user123', company_id='company456'),
            platform='whatsapp',
            session_id=1,
            menu=Menu(name='Suporte'),
            user=user,
            route='start',
        )
        return UserCall(
            user_state=user_state,
            message=sample_message,
            router_client=mock_router_client,
        )

    @pytest.fixture
    def user_call_no_menu(self, sample_message, mock_router_client):
        user = User(
            data=UserData(name='João Silva', cpf='11111111111'),
            identity=UserIdentity(
                auth_level=AuthLevel.READ, cpf='11111111111'
            ),
        )
        user_state = UserState(
            chat_id=ChatID(user_id='user123', company_id='company456'),
            platform='whatsapp',
            session_id=1,
            menu=None,
            user=user,
            route='start',
        )
        return UserCall(
            user_state=user_state,
            message=sample_message,
            router_client=mock_router_client,
        )

    @pytest.fixture
    def user_call_menu_no_name(self, sample_message, mock_router_client):
        user = User(
            data=UserData(name='João Silva', cpf='11111111111'),
            identity=UserIdentity(
                auth_level=AuthLevel.READ, cpf='11111111111'
            ),
        )
        user_state = UserState(
            chat_id=ChatID(user_id='user123', company_id='company456'),
            platform='whatsapp',
            session_id=1,
            menu=Menu(name=None),
            user=user,
            route='start',
        )
        return UserCall(
            user_state=user_state,
            message=sample_message,
            router_client=mock_router_client,
        )

    @pytest.fixture
    def user_call_cpf_none(self, sample_message, mock_router_client):
        user = User(
            data=UserData(name='João Silva', cpf=None),
            identity=UserIdentity(auth_level=AuthLevel.READ),
        )
        user_state = UserState(
            chat_id=ChatID(user_id='user123', company_id='company456'),
            platform='whatsapp',
            session_id=1,
            menu=Menu(name='Suporte'),
            user=user,
            route='start',
        )
        return UserCall(
            user_state=user_state,
            message=sample_message,
            router_client=mock_router_client,
        )

    @pytest.mark.asyncio
    async def test_associate_cpf_chamado_quando_cpf_diferente(
        self, user_call_with_menu, mock_router_client
    ):
        """associate_cpf é chamado uma vez quando observation["cpf"] difere do cpf atual."""
        mock_router_client.update_session_observation = AsyncMock()
        mock_router_client.associate_cpf = AsyncMock()

        await user_call_with_menu.add_observation({'cpf': '99999999999'})

        mock_router_client.associate_cpf.assert_called_once()
        call_kwargs = mock_router_client.associate_cpf.call_args
        assert call_kwargs.kwargs['cpf'] == '99999999999'

    @pytest.mark.asyncio
    async def test_associate_cpf_nao_chamado_quando_cpf_igual(
        self, user_call_with_menu, mock_router_client
    ):
        """associate_cpf não é chamado quando observation["cpf"] é igual ao cpf atual."""
        mock_router_client.update_session_observation = AsyncMock()
        mock_router_client.associate_cpf = AsyncMock()

        await user_call_with_menu.add_observation({'cpf': '11111111111'})

        mock_router_client.associate_cpf.assert_not_called()

    @pytest.mark.asyncio
    async def test_associate_cpf_nao_chamado_sem_chave_cpf(
        self, user_call_with_menu, mock_router_client
    ):
        """associate_cpf não é chamado quando observation não contém "cpf"."""
        mock_router_client.update_session_observation = AsyncMock()
        mock_router_client.associate_cpf = AsyncMock()

        await user_call_with_menu.add_observation({'nome': 'Maria'})

        mock_router_client.associate_cpf.assert_not_called()

    @pytest.mark.asyncio
    async def test_associate_cpf_chamado_quando_cpf_atual_none(
        self, user_call_cpf_none, mock_router_client
    ):
        """associate_cpf é chamado quando user.identity.cpf é None."""
        mock_router_client.update_session_observation = AsyncMock()
        mock_router_client.associate_cpf = AsyncMock()

        await user_call_cpf_none.add_observation({'cpf': '22222222222'})

        mock_router_client.associate_cpf.assert_called_once()

    @pytest.mark.asyncio
    async def test_source_e_menu_name_quando_menu_disponivel(
        self, user_call_with_menu, mock_router_client
    ):
        """source é menu.name quando menu e menu.name estão disponíveis."""
        mock_router_client.update_session_observation = AsyncMock()
        mock_router_client.associate_cpf = AsyncMock()

        await user_call_with_menu.add_observation({'cpf': '99999999999'})

        call_kwargs = mock_router_client.associate_cpf.call_args
        assert call_kwargs.kwargs['source'] == 'Suporte'

    @pytest.mark.asyncio
    async def test_source_e_chatbot_quando_menu_none(
        self, user_call_no_menu, mock_router_client
    ):
        """source é "chatbot" quando menu é None."""
        mock_router_client.update_session_observation = AsyncMock()
        mock_router_client.associate_cpf = AsyncMock()

        await user_call_no_menu.add_observation({'cpf': '99999999999'})

        call_kwargs = mock_router_client.associate_cpf.call_args
        assert call_kwargs.kwargs['source'] == 'chatbot'

    @pytest.mark.asyncio
    async def test_source_e_chatbot_quando_menu_name_none(
        self, user_call_menu_no_name, mock_router_client
    ):
        """source é "chatbot" quando menu.name é None."""
        mock_router_client.update_session_observation = AsyncMock()
        mock_router_client.associate_cpf = AsyncMock()

        await user_call_menu_no_name.add_observation({'cpf': '99999999999'})

        call_kwargs = mock_router_client.associate_cpf.call_args
        assert call_kwargs.kwargs['source'] == 'chatbot'

    @pytest.mark.asyncio
    async def test_phone_e_company_id(
        self, user_call_with_menu, mock_router_client
    ):
        """phone passado para associate_cpf é igual a company_id."""
        mock_router_client.update_session_observation = AsyncMock()
        mock_router_client.associate_cpf = AsyncMock()

        await user_call_with_menu.add_observation({'cpf': '99999999999'})

        call_kwargs = mock_router_client.associate_cpf.call_args
        assert call_kwargs.kwargs['phone'] == 'company456'


@pytest.mark.unit
class TestLoadIdentity:
    """Testes para o método load_identity de UserCall."""

    @pytest.mark.asyncio
    async def test_load_identity_updates_user_state(
        self, user_call, mock_router_client
    ):
        """Happy path: get_identity retorna UserIdentity e user.identity é atualizado."""
        expected_identity = UserIdentity(auth_level=AuthLevel.WRITE)
        mock_router_client.get_identity = AsyncMock(
            return_value=expected_identity
        )

        result = await user_call.load_identity()

        assert result is expected_identity
        assert user_call.user.identity is expected_identity

    @pytest.mark.asyncio
    async def test_load_identity_initializes_user_if_none(
        self, sample_message, mock_router_client
    ):
        """user_state.user é None antes; após load_identity, user não é None e identity está correto."""
        user_state = UserState(
            chat_id=ChatID(user_id='user123', company_id='company456'),
            platform='whatsapp',
            session_id=1,
            menu=Menu(name='Suporte'),
            user=None,
            route='start',
        )
        uc = UserCall(
            user_state=user_state,
            message=sample_message,
            router_client=mock_router_client,
        )
        expected_identity = UserIdentity(auth_level=AuthLevel.READ)
        mock_router_client.get_identity = AsyncMock(
            return_value=expected_identity
        )

        await uc.load_identity()

        assert user_state.user is not None
        assert user_state.user.identity is expected_identity

    @pytest.mark.asyncio
    async def test_load_identity_passes_cpf(
        self, user_call, mock_router_client
    ):
        """cpf fornecido é repassado para router_client.get_identity."""
        expected_identity = UserIdentity(auth_level=AuthLevel.READ)
        mock_router_client.get_identity = AsyncMock(
            return_value=expected_identity
        )

        await user_call.load_identity(cpf='12345678900')

        mock_router_client.get_identity.assert_called_once_with(
            'user123', cpf='12345678900'
        )

    @pytest.mark.asyncio
    async def test_load_identity_raises_on_error(
        self, user_call, mock_router_client
    ):
        """Exceção em get_identity é capturada e re-raised como ValueError."""
        mock_router_client.get_identity = AsyncMock(
            side_effect=Exception('falha na api')
        )

        with pytest.raises(ValueError, match='Erro ao carregar identidade'):
            await user_call.load_identity()


@pytest.mark.unit
class TestLoadUserstate:
    """Testes para o método load_userstate de UserCall."""

    @pytest.mark.asyncio
    async def test_load_userstate_updates_state(
        self, user_call, mock_router_client, sample_user_state
    ):
        """Happy path: get_session_by_chat_id retorna novo UserState; __user_state é substituído e retornado."""
        new_user_state = UserState(
            chat_id=ChatID(user_id='user123', company_id='company456'),
            platform='whatsapp',
            session_id=2,
            menu=Menu(name='Vendas'),
            user=sample_user_state.user,
            route='outro',
        )
        mock_router_client.get_session_by_chat_id = AsyncMock(
            return_value=new_user_state
        )

        result = await user_call.load_userstate()

        assert result is new_user_state
        assert user_call._UserCall__user_state is new_user_state

    @pytest.mark.asyncio
    async def test_load_userstate_raises_if_none(
        self, user_call, mock_router_client
    ):
        """get_session_by_chat_id retorna None → método lança ValueError."""
        mock_router_client.get_session_by_chat_id = AsyncMock(
            return_value=None
        )

        with pytest.raises(ValueError, match='Sessão não encontrada'):
            await user_call.load_userstate()

    @pytest.mark.asyncio
    async def test_load_userstate_raises_on_error(
        self, user_call, mock_router_client
    ):
        """Exceção em get_session_by_chat_id é capturada e re-raised como ValueError."""
        mock_router_client.get_session_by_chat_id = AsyncMock(
            side_effect=Exception('timeout')
        )

        with pytest.raises(ValueError, match='Erro ao carregar userstate'):
            await user_call.load_userstate()

    @pytest.mark.asyncio
    async def test_load_userstate_passes_chat_id(
        self, user_call, mock_router_client, sample_user_state
    ):
        """get_session_by_chat_id é chamado com o chat_id correto."""
        new_user_state = UserState(
            chat_id=ChatID(user_id='user123', company_id='company456'),
            platform='whatsapp',
            session_id=2,
            menu=Menu(name='Suporte'),
            user=sample_user_state.user,
            route='start',
        )
        mock_router_client.get_session_by_chat_id = AsyncMock(
            return_value=new_user_state
        )

        await user_call.load_userstate()

        mock_router_client.get_session_by_chat_id.assert_called_once_with(
            sample_user_state.chat_id
        )


@pytest.mark.unit
class TestPlatformState:
    """Testes para a property platform_state de UserCall."""

    def test_platform_state_returns_injected_object(
        self, sample_user_state, sample_message, mock_router_client
    ):
        ps = PlatformState(
            data={
                'session_id': 1,
                'customer_id': 'CUST001',
                'platform': 'whatsapp_enterprise',
                'protocol': 'P001',
                'campaign': 'C.TEST',
            }
        )
        uc = UserCall(
            user_state=sample_user_state,
            message=sample_message,
            router_client=mock_router_client,
            platform_state=ps,
        )
        assert uc.platform_state is ps
        assert uc.platform_state.data['protocol'] == 'P001'

    def test_platform_state_default_is_empty(
        self, sample_user_state, sample_message, mock_router_client
    ):
        uc = UserCall(
            user_state=sample_user_state,
            message=sample_message,
            router_client=mock_router_client,
        )
        assert isinstance(uc.platform_state, PlatformState)
        assert bool(uc.platform_state) is False


@pytest.mark.unit
class TestUserStateProperty:
    """Testes para a property user_state de UserCall."""

    def test_user_state_returns_injected_object(
        self, sample_user_state, sample_message, mock_router_client
    ):
        uc = UserCall(
            user_state=sample_user_state,
            message=sample_message,
            router_client=mock_router_client,
        )
        assert uc.user_state is sample_user_state
        assert uc.user_state.platform == 'whatsapp'
        assert uc.user_state.chat_id.user_id == 'user123'
        assert uc.user_state.chat_id.company_id == 'company456'

    def test_user_state_reflects_mutation(
        self, sample_user_state, sample_message, mock_router_client
    ):
        uc = UserCall(
            user_state=sample_user_state,
            message=sample_message,
            router_client=mock_router_client,
        )
        sample_user_state.route = 'menu.vendas'
        assert uc.user_state.route == 'menu.vendas'

    def test_user_state_returns_none_when_none(
        self, sample_message, mock_router_client
    ):
        uc = UserCall(
            user_state=None,
            message=sample_message,
            router_client=mock_router_client,
        )
        assert uc.user_state is None


@pytest.mark.unit
class TestSendException:
    """Testes para a exceção levantada por __send de UserCall."""

    @pytest.mark.asyncio
    async def test_send_exception_does_not_contain_chatid_prefix(
        self, sample_user_state, mock_router_client
    ):
        """Exceção de __send NÃO deve conter o prefixo [ChatID:]."""
        from chatgraph.models.message import Message

        mock_router_client.send_message = AsyncMock(
            side_effect=Exception('timeout')
        )
        uc = UserCall(
            user_state=sample_user_state,
            message=Message('Olá'),
            router_client=mock_router_client,
        )
        msg = Message('Teste')

        with pytest.raises(Exception, match='Erro ao enviar mensagem'):
            await uc._UserCall__send(msg)
