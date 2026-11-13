# ruff: noqa: PLR6301 - testes em classe, como nos demais arquivos de
# tests/unit.
"""
Testes para UserCall.send_url_button.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatgraph.history.entry import HistoryEventType
from chatgraph.history.store import MemoryHistoryStore
from chatgraph.models.message import File, Message, SendType
from chatgraph.models.url_button import (
    URLButtonInvalidError,
    URLButtonMessage,
)
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

URL = 'https://exemplo.com.br/fatura/98765'
BODY = 'Sua fatura de novembro já está disponível.'


def make(**changes) -> URLButtonMessage:
    base = {
        'header': 'Sua fatura',
        'body': BODY,
        'footer': 'Verdecard',
        'label': 'Ver fatura',
        'url': URL,
    }
    return URLButtonMessage(**{**base, **changes})


@pytest.fixture
def user_state():
    return UserState(
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


@pytest.fixture
def router_client():
    client = MagicMock()
    client.send_message = AsyncMock(return_value=True)
    client.get_file = AsyncMock()
    client.upload_file = AsyncMock()
    return client


@pytest.fixture
def store():
    return MemoryHistoryStore()


@pytest.fixture
def user_call(user_state, router_client, store):
    return UserCall(
        user_state=user_state,
        message=Message('Olá'),
        router_client=router_client,
        history_store=store,
    )


@pytest.fixture
def local_file(tmp_path):
    path = tmp_path / 'fatura.png'
    path.write_bytes(b'\x89PNG fake')
    return File(name=str(path))


@pytest.mark.unit
class TestSendURLButton:
    @pytest.mark.asyncio
    async def test_valid_message_without_file_is_sent_once(
        self, user_call, router_client
    ):
        m = make()

        await user_call.send_url_button(m)

        router_client.send_message.assert_awaited_once()
        sent = router_client.send_message.await_args.args[0]
        assert sent.buttons == m.to_message().buttons
        assert sent.text_message == m.to_message().text_message
        assert sent.file is None
        router_client.get_file.assert_not_called()
        router_client.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_message_is_not_sent(
        self, user_call, router_client, store
    ):
        with pytest.raises(URLButtonInvalidError) as exc_info:
            await user_call.send_url_button(make(body=''))

        assert exc_info.value.reason == 'body_empty'
        router_client.send_message.assert_not_called()
        router_client.get_file.assert_not_called()
        router_client.upload_file.assert_not_called()
        assert await store.get('user123:company456', 1) == []

    @pytest.mark.asyncio
    async def test_invalid_text_with_local_file_does_not_upload(
        self, user_call, router_client, local_file
    ):
        m = make(header='', label='', file=local_file)

        with pytest.raises(URLButtonInvalidError) as exc_info:
            await user_call.send_url_button(m)

        assert exc_info.value.reason == 'label_empty'
        router_client.get_file.assert_not_called()
        router_client.upload_file.assert_not_called()
        router_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_file_with_id_is_sent_without_upload(
        self, user_call, router_client
    ):
        file = File(id='abc', send_type=SendType.IMAGE)

        await user_call.send_url_button(make(header='', file=file))

        router_client.get_file.assert_not_called()
        router_client.upload_file.assert_not_called()
        sent = router_client.send_message.await_args.args[0]
        assert sent.file.id == 'abc'

    @pytest.mark.asyncio
    async def test_local_file_is_uploaded_and_bot_file_is_untouched(
        self, user_call, router_client, local_file
    ):
        router_client.get_file.return_value = File()
        router_client.upload_file.return_value = File(
            id='up1',
            url='https://storage.exemplo/x',
            send_type=SendType.IMAGE,
            mime_type='image/png',
        )
        m = make(header='', file=local_file)

        await user_call.send_url_button(m)

        router_client.upload_file.assert_awaited_once()
        sent = router_client.send_message.await_args.args[0]
        assert sent.file.id == 'up1'
        assert not local_file.id
        assert local_file.bytes_data is None
        assert m.file is local_file

    @pytest.mark.asyncio
    async def test_local_file_returned_as_audio_is_rejected(
        self, user_call, router_client, local_file
    ):
        router_client.get_file.return_value = File()
        router_client.upload_file.return_value = File(
            id='up2', send_type=SendType.AUDIO
        )

        with pytest.raises(URLButtonInvalidError) as exc_info:
            await user_call.send_url_button(make(header='', file=local_file))

        assert exc_info.value.reason == 'file_type_unsupported'
        router_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_router_error_is_wrapped(self, user_call, router_client):
        router_client.send_message.side_effect = RuntimeError('router down')

        with pytest.raises(Exception, match='Erro ao enviar mensagem'):
            await user_call.send_url_button(make())

    @pytest.mark.asyncio
    async def test_valid_send_records_url_button_in_history(
        self, user_call, store
    ):
        await user_call.send_url_button(make())

        entries = await store.get('user123:company456', 1)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.event_type == HistoryEventType.MESSAGE_OUT
        assert entry.message['buttons'] == [
            {'type': 'url', 'title': 'Ver fatura', 'detail': URL}
        ]
