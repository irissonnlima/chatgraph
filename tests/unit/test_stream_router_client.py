# ruff: noqa: PLR6301, PLR2004 - testes em classe e literais nos asserts, como no
# resto da suíte.
import json

import httpx
import pytest
import pytest_asyncio

from chatgraph.models.actions import EndAction
from chatgraph.models.http_responses import RouterResponses
from chatgraph.models.message import File, Message
from chatgraph.models.platform_state import PlatformState
from chatgraph.models.userstate import ChatID, Menu, UserState
from chatgraph.services.router_http_client import RouterHTTPClient
from chatgraph.stream.errors import SessionNotOwnedError
from chatgraph.stream.router_client import RouterStreamClient

BASE_URL = 'http://localhost:8080/v1/actions'
CHAT_ID = ChatID(user_id='user-1', company_id='company-1')


class RecordingCommand:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, ChatID, dict, bool]] = []
        self._error = error

    async def __call__(
        self, name: str, chat_id: ChatID, payload: dict, idempotent: bool
    ) -> None:
        self.calls.append((name, chat_id, payload, idempotent))
        if self._error is not None:
            raise self._error


def make_user_state() -> UserState:
    return UserState(chat_id=CHAT_ID, platform='voll', route='start')


def make_end_action() -> EndAction:
    return EndAction(
        id='ea-1',
        name='Resolvido',
        description='fim',
        department_id=7,
        observation='obs',
        last_update='2026-09-30T10:00:00',
    )


@pytest.fixture
def recorder():
    return RecordingCommand()


@pytest_asyncio.fixture
async def stream_router_client(recorder):
    client = RouterStreamClient(BASE_URL, recorder, 'u', 'p')
    yield client
    await client.close()


@pytest.mark.unit
class TestRouterStreamClientPayloads:
    @pytest.mark.asyncio
    async def test_send_message_with_platform_state(
        self, stream_router_client, recorder
    ):
        message = Message(text_message='oi')
        user_state = make_user_state()
        platform_state = PlatformState(data={'voll': {'a': 1}})

        await stream_router_client.send_message(
            message, user_state, platform_state
        )

        assert recorder.calls == [
            (
                'send',
                CHAT_ID,
                {
                    'message': message.to_dict(),
                    'user_state': user_state.to_dict(),
                    'platform_state': {'voll': {'a': 1}},
                },
                False,
            )
        ]

    @pytest.mark.asyncio
    async def test_send_message_without_platform_state_omits_key(
        self, stream_router_client, recorder
    ):
        message = Message(text_message='oi')
        user_state = make_user_state()

        await stream_router_client.send_message(message, user_state)

        name, chat_id, payload, idempotent = recorder.calls[0]
        assert (name, chat_id, idempotent) == ('send', CHAT_ID, False)
        assert payload == {
            'message': message.to_dict(),
            'user_state': user_state.to_dict(),
        }
        assert payload['user_state']['chat_id'] == CHAT_ID.to_dict()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        'platform_state',
        [PlatformState(), PlatformState(data={'voll': {'a': 1}})],
        ids=['without_platform_state', 'with_platform_state'],
    )
    async def test_send_payload_is_identical_to_the_http_body(
        self, stream_router_client, recorder, respx_mock, platform_state
    ):
        route = respx_mock.post(f'{BASE_URL}/messages/send/').mock(
            return_value=httpx.Response(
                200, json={'status': True, 'message': 'ok'}
            )
        )
        message = Message(text_message='oi')
        user_state = make_user_state()
        http_client = RouterHTTPClient(BASE_URL, 'u', 'p')
        try:
            await http_client.send_message(message, user_state, platform_state)
        finally:
            await http_client.close()

        await stream_router_client.send_message(
            message, user_state, platform_state
        )

        http_body = json.loads(route.calls[0].request.content)
        assert recorder.calls[0][2] == http_body

    @pytest.mark.asyncio
    async def test_set_session_route(self, stream_router_client, recorder):
        await stream_router_client.set_session_route(CHAT_ID, 'start.menu')

        assert recorder.calls == [
            ('set_route', CHAT_ID, {'route': 'start.menu'}, True)
        ]

    @pytest.mark.asyncio
    async def test_update_session_observation(
        self, stream_router_client, recorder
    ):
        await stream_router_client.update_session_observation(
            CHAT_ID, '{"step":2}'
        )

        assert recorder.calls == [
            (
                'set_observation',
                CHAT_ID,
                {'observation': '{"step":2}'},
                True,
            )
        ]

    @pytest.mark.asyncio
    async def test_end_chat_carries_the_six_end_action_fields(
        self, stream_router_client, recorder
    ):
        await stream_router_client.end_chat(CHAT_ID, make_end_action(), 'bot')

        assert recorder.calls == [
            (
                'end_session',
                CHAT_ID,
                {
                    'end_action': {
                        'id': 'ea-1',
                        'name': 'Resolvido',
                        'description': 'fim',
                        'department_id': 7,
                        'observation': 'obs',
                        'last_update': '2026-09-30T10:00:00',
                    },
                    'origin': 'bot',
                },
                False,
            )
        ]

    @pytest.mark.asyncio
    async def test_transfer_to_menu_without_route_omits_key(
        self, stream_router_client, recorder
    ):
        message = Message(text_message='transferindo')

        await stream_router_client.transfer_to_menu(
            CHAT_ID, Menu(id=3, name='financeiro'), message
        )

        assert recorder.calls == [
            (
                'transfer_to_menu',
                CHAT_ID,
                {'menu': 'financeiro', 'message': message.to_dict()},
                False,
            )
        ]

    @pytest.mark.asyncio
    async def test_transfer_to_menu_with_route(
        self, stream_router_client, recorder
    ):
        message = Message(text_message='')

        await stream_router_client.transfer_to_menu(
            CHAT_ID, Menu(name='financeiro'), message, route='inicio'
        )

        assert recorder.calls[0][2] == {
            'menu': 'financeiro',
            'message': message.to_dict(),
            'route': 'inicio',
        }


@pytest.mark.unit
class TestRouterStreamClientContract:
    @pytest.mark.asyncio
    async def test_only_set_route_and_set_observation_are_idempotent(
        self, stream_router_client, recorder
    ):
        message = Message(text_message='oi')
        await stream_router_client.send_message(message, make_user_state())
        await stream_router_client.set_session_route(CHAT_ID, 'r')
        await stream_router_client.update_session_observation(CHAT_ID, 'o')
        await stream_router_client.end_chat(CHAT_ID, make_end_action(), 'bot')
        await stream_router_client.transfer_to_menu(
            CHAT_ID, Menu(name='m'), message
        )

        flags = {name: idem for name, _, _, idem in recorder.calls}
        assert flags == {
            'send': False,
            'set_route': True,
            'set_observation': True,
            'end_session': False,
            'transfer_to_menu': False,
        }

    @pytest.mark.asyncio
    async def test_every_action_returns_a_truthy_ok_response(
        self, stream_router_client
    ):
        message = Message(text_message='oi')
        responses = [
            await stream_router_client.send_message(
                message, make_user_state()
            ),
            await stream_router_client.set_session_route(CHAT_ID, 'r'),
            await stream_router_client.update_session_observation(
                CHAT_ID, 'o'
            ),
            await stream_router_client.end_chat(
                CHAT_ID, make_end_action(), 'bot'
            ),
            await stream_router_client.transfer_to_menu(
                CHAT_ID, Menu(name='m'), message
            ),
        ]

        for response in responses:
            assert isinstance(response, RouterResponses)
            assert response.status is True
            assert response

    @pytest.mark.asyncio
    async def test_command_exception_propagates_unwrapped(self):
        error = SessionNotOwnedError('session_not_owned: on menu geral')
        client = RouterStreamClient(BASE_URL, RecordingCommand(error))
        try:
            with pytest.raises(SessionNotOwnedError) as exc_info:
                await client.set_session_route(CHAT_ID, 'r')
        finally:
            await client.close()

        assert exc_info.value is error

    @pytest.mark.asyncio
    async def test_inherits_http_credentials(self):
        client = RouterStreamClient(
            BASE_URL, RecordingCommand(), 'user', 'secret', 12.0
        )
        try:
            assert client._bearer_token == 'secret'
            assert client.timeout == 12.0
            assert str(client._actions_client.base_url) == (
                'http://localhost:8080/v1/actions/'
            )
        finally:
            await client.close()


@pytest.mark.unit
class TestRouterStreamClientHttpFallback:
    @pytest.mark.asyncio
    async def test_files_end_action_and_id_positiva_stay_on_http(
        self, stream_router_client, recorder, respx_mock
    ):
        ok = {'status': True, 'message': 'ok'}
        upload = respx_mock.post(f'{BASE_URL}/files/upload/').mock(
            return_value=httpx.Response(
                201, json={**ok, 'data': {'id': 'f1', 'name': 'a.txt'}}
            )
        )
        get_file = respx_mock.get(f'{BASE_URL}/files/f1/').mock(
            return_value=httpx.Response(
                200, json={**ok, 'data': {'id': 'f1', 'name': 'a.txt'}}
            )
        )
        end_action = respx_mock.get(f'{BASE_URL}/end_actions/').mock(
            return_value=httpx.Response(
                200, json={**ok, 'data': {'id': 'ea-1', 'name': 'x'}}
            )
        )
        associate = respx_mock.post(
            'http://localhost:8080/v1/id-positiva/associate-cpf'
        ).mock(return_value=httpx.Response(200, json=ok))
        identity = respx_mock.get(
            'http://localhost:8080/v1/id-positiva/identity'
        ).mock(return_value=httpx.Response(200, json={**ok, 'data': {}}))

        await stream_router_client.upload_file(
            File(bytes_data=b'abc', name='a.txt')
        )
        await stream_router_client.get_file('f1')
        await stream_router_client.get_end_action(end_action_id='ea-1')
        await stream_router_client.associate_cpf(
            CHAT_ID, cpf='12345678900', source='chatbot'
        )
        await stream_router_client.get_identity('user-1')

        for route in (upload, get_file, end_action, associate, identity):
            assert route.call_count == 1
        assert recorder.calls == []
