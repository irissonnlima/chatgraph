# ruff: noqa: PLR6301, PLR2004 - testes em classe e literais nos asserts, como no
# resto da suíte.
import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatgraph.messages.turn import build_usercall, publish_edge_error
from chatgraph.models.log_envelope import mark_error_logged
from chatgraph.types.usercall import UserCall


def make_frame(observation: str = '{"k":"v"}', **extra) -> dict:
    frame = {
        'user_state': {
            'chat_id': {'user_id': 'user-1', 'company_id': 'company-1'},
            'platform': 'voll',
            'observation': observation,
            'menu': {'id': 5, 'name': 'rh'},
            'session_id': 77,
            'route': 'start',
        },
        'message': {'text_message': {'title': '', 'detail': 'oi'}},
    }
    frame.update(extra)
    return frame


@pytest.fixture
def log_publisher():
    publisher = MagicMock()
    publisher.publish_error = AsyncMock()
    return publisher


@pytest.mark.unit
class TestBuildUsercall:
    def test_valid_observation_builds_usercall_with_given_client(self):
        router_client = MagicMock()
        history_store = MagicMock()

        usercall = build_usercall(make_frame(), router_client, history_store)

        assert isinstance(usercall, UserCall)
        assert usercall._UserCall__router_client is router_client
        assert usercall._UserCall__history_store is history_store
        assert usercall.user_id == 'user-1'
        assert usercall.content_message == 'oi'

    def test_invalid_observation_raises_json_decode_error(self):
        with pytest.raises(json.JSONDecodeError):
            build_usercall(make_frame('texto'), MagicMock(), None)

    def test_missing_observation_defaults_to_empty_object(self):
        frame = make_frame()
        del frame['user_state']['observation']

        usercall = build_usercall(frame, MagicMock(), None)

        assert isinstance(usercall, UserCall)

    def test_non_dict_platform_state_is_ignored(self):
        usercall = build_usercall(
            make_frame(platform_state='lixo'), MagicMock(), None
        )

        assert isinstance(usercall, UserCall)


@pytest.mark.unit
class TestPublishEdgeError:
    @pytest.mark.asyncio
    async def test_with_usercall_uses_menu_origin(self, log_publisher):
        usercall = build_usercall(make_frame(), MagicMock(), None)

        await publish_edge_error(log_publisher, RuntimeError('boom'), usercall)

        envelope = log_publisher.publish_error.await_args.args[0]
        assert envelope.origin == 'chatgraph:rh'
        assert envelope.chat_user_id == 'user-1'
        assert envelope.chat_company_id == 'company-1'
        assert envelope.session_id == 77
        assert envelope.error == 'boom'
        assert 'RuntimeError' in envelope.payload['error_message']

    @pytest.mark.asyncio
    async def test_without_usercall_uses_unknown_origin(self, log_publisher):
        await publish_edge_error(log_publisher, ValueError('x'), None)

        envelope = log_publisher.publish_error.await_args.args[0]
        assert envelope.origin == 'chatgraph:unknown'

    @pytest.mark.asyncio
    async def test_traceback_is_included_outside_except_block(
        self, log_publisher
    ):
        try:
            raise RuntimeError('boom')
        except RuntimeError as exc:
            error = exc

        await publish_edge_error(log_publisher, error, None)

        envelope = log_publisher.publish_error.await_args.args[0]
        assert 'Traceback' in envelope.payload['error_message']
        assert 'NoneType: None' not in envelope.payload['error_message']

    @pytest.mark.asyncio
    async def test_already_logged_error_is_not_published(self, log_publisher):
        error = RuntimeError('boom')
        mark_error_logged(error)

        await publish_edge_error(log_publisher, error, None)

        log_publisher.publish_error.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_without_publisher_is_a_noop(self):
        await publish_edge_error(None, RuntimeError('boom'), None)

    @pytest.mark.asyncio
    async def test_publish_failure_only_logs_warning(
        self, log_publisher, caplog
    ):
        caplog.set_level(logging.WARNING, logger='chatgraph.system')
        log_publisher.publish_error.side_effect = ConnectionError('down')

        await publish_edge_error(log_publisher, RuntimeError('boom'), None)

        assert any(
            'Falha ao publicar log_error: down' in r.getMessage()
            for r in caplog.records
        )
