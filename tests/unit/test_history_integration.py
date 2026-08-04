"""Testes de integração entre UserCall e HistoryStore."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatgraph.bot.chatbot_model import ChatbotApp
from chatgraph.error.chatbot_error import ChatbotMessageError
from chatgraph.history.entry import HistoryEventType, HistoryRole
from chatgraph.history.store import MemoryHistoryStore
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
def store():
    return MemoryHistoryStore()


@pytest.fixture
def mock_router_client():
    client = MagicMock()
    client.send_message = AsyncMock(return_value=True)
    client.set_session_route = AsyncMock(return_value=True)
    client.transfer_to_menu = AsyncMock(return_value=True)
    client.end_chat = AsyncMock(return_value=True)
    client.get_end_action = AsyncMock(return_value=MagicMock())
    return client


def _make_usercall(user_state, router_client, history_store=None):
    return UserCall(
        user_state=user_state,
        message=Message('Olá'),
        router_client=router_client,
        history_store=history_store,
    )


@pytest.mark.unit
class TestUserCallHistoryIntegration:
    """Testes de integração UserCall + HistoryStore."""

    @pytest.mark.asyncio
    async def test_t1_send_records_message_out(
        self,
        sample_user_state,
        mock_router_client,
        store,
    ):
        usercall = _make_usercall(
            sample_user_state, mock_router_client, history_store=store
        )

        await usercall.send(Message('oi'))

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.role is HistoryRole.BOT
        assert entry.event_type is HistoryEventType.MESSAGE_OUT
        assert entry.message is not None

    @pytest.mark.asyncio
    async def test_t2_set_route_records_route_change(
        self,
        sample_user_state,
        mock_router_client,
        store,
    ):
        usercall = _make_usercall(
            sample_user_state, mock_router_client, history_store=store
        )

        await usercall.set_route('subrota')

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.role is HistoryRole.SYSTEM
        assert entry.event_type is HistoryEventType.ROUTE_CHANGE
        assert entry.metadata['new_route'] == 'start.subrota'

    @pytest.mark.asyncio
    async def test_t3_transfer_to_menu_records_transfer(
        self,
        sample_user_state,
        mock_router_client,
        store,
    ):
        usercall = _make_usercall(
            sample_user_state, mock_router_client, history_store=store
        )

        await usercall.transfer_to_menu('MenuDestino', 'mensagem')

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.role is HistoryRole.SYSTEM
        assert entry.event_type is HistoryEventType.TRANSFER
        assert entry.metadata['menu'] == 'MenuDestino'
        assert entry.metadata['user_message'] == 'mensagem'

    @pytest.mark.asyncio
    async def test_t4_end_chat_records_end_chat(
        self,
        sample_user_state,
        mock_router_client,
        store,
    ):
        usercall = _make_usercall(
            sample_user_state, mock_router_client, history_store=store
        )

        await usercall.end_chat(end_action_id='1', end_action_name='fim')

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.role is HistoryRole.SYSTEM
        assert entry.event_type is HistoryEventType.END_CHAT
        assert entry.metadata['end_action_id'] == '1'
        assert entry.metadata['end_action_name'] == 'fim'

    @pytest.mark.asyncio
    async def test_t5_no_store_no_error(
        self,
        sample_user_state,
        mock_router_client,
    ):
        usercall = _make_usercall(
            sample_user_state, mock_router_client, history_store=None
        )

        await usercall.send(Message('oi'))
        await usercall.set_route('subrota')
        await usercall.transfer_to_menu('Menu', 'msg')
        await usercall.end_chat(end_action_id='1', end_action_name='fim')

        assert usercall.history is None

    @pytest.mark.asyncio
    async def test_t6_duplicate_send_does_not_duplicate_history(
        self,
        sample_user_state,
        mock_router_client,
        store,
    ):
        usercall = _make_usercall(
            sample_user_state, mock_router_client, history_store=store
        )
        msg = Message('oi')

        await usercall.send(msg)
        await usercall.send(msg)

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        assert entries[0].event_type is HistoryEventType.MESSAGE_OUT

    @pytest.mark.asyncio
    async def test_t7_duplicate_send_with_distinct_message_instances(
        self,
        sample_user_state,
        mock_router_client,
        store,
    ):
        """Simula reprocessamento real: duas instâncias distintas de
        Message com mesmo conteúdo e mesmo date_time devem deduplicar.
        """
        usercall = _make_usercall(
            sample_user_state, mock_router_client, history_store=store
        )
        fixed_dt = datetime(2024, 1, 1, 12, 0, 0)
        msg1 = Message('oi', date_time=fixed_dt)
        msg2 = Message('oi', date_time=fixed_dt)

        await usercall.send(msg1)
        await usercall.send(msg2)

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        assert entries[0].event_type is HistoryEventType.MESSAGE_OUT


@pytest.mark.unit
class TestChatbotAppMessageInHook:
    """Testa o hook MESSAGE_IN em ChatbotApp.process_message."""

    @staticmethod
    def _make_app(store):
        consumer = MagicMock()
        consumer.set_history_store = MagicMock()
        return ChatbotApp(
            message_consumer=consumer,
            history_store=store,
            guard=None,
        )

    @staticmethod
    def _make_usercall(message_text='Olá'):
        user_state = UserState(
            chat_id=ChatID(user_id='user123', company_id='company456'),
            platform='whatsapp',
            session_id=1,
            menu=Menu(name='Suporte'),
            user=User(
                data=UserData(name='João Silva'),
                identity=UserIdentity(auth_level=AuthLevel.READ),
            ),
            route='start',
        )
        return UserCall(
            user_state=user_state,
            message=Message(message_text),
            router_client=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_message_in_records_full_message_dict(self):
        store = MemoryHistoryStore()
        app = self._make_app(store)
        usercall = self._make_usercall('Olá, tudo bem?')

        mock_process = AsyncMock()
        with patch.object(
            app, '_ChatbotApp__process_func_response', new=mock_process
        ):
            # Rota inexistente gera ChatbotMessageError, mas o registro
            # de MESSAGE_IN já ocorre antes da busca da rota.
            with pytest.raises(ChatbotMessageError):
                await app.process_message(usercall)

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.role is HistoryRole.USER
        assert entry.event_type is HistoryEventType.MESSAGE_IN
        assert entry.message == usercall.message.to_dict()
        assert entry.message['text_message']['detail'] == 'Olá, tudo bem?'

    @pytest.mark.asyncio
    async def test_message_in_idempotent_on_reprocess(self):
        store = MemoryHistoryStore()
        app = self._make_app(store)

        mock_process = AsyncMock()
        with patch.object(
            app, '_ChatbotApp__process_func_response', new=mock_process
        ):
            usercall = self._make_usercall('Olá')
            with pytest.raises(ChatbotMessageError):
                await app.process_message(usercall)

            # Segunda chamada com mesma Message (simula reprocessamento)
            usercall2 = self._make_usercall('Olá')
            # Garante mesmo date_time para que to_dict seja idêntico
            usercall2._UserCall__message.date_time = (
                usercall._UserCall__message.date_time
            )
            with pytest.raises(ChatbotMessageError):
                await app.process_message(usercall2)

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        assert entries[0].event_type is HistoryEventType.MESSAGE_IN
