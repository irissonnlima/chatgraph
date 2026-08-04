import json

import pytest

from chatgraph.error.chatbot_error import ChatbotMessageError
from chatgraph.models.log_envelope import (
    ErrorLogPayload,
    EventType,
    LogEnvelope,
    error_code_from_exception,
)


@pytest.mark.unit
class TestErrorCodeFromException:
    def test_error_code_from_exception_known(self):
        exc = ChatbotMessageError('user1', 'test error')
        result = error_code_from_exception(exc)
        assert result == 'CHATBOT_MESSAGE_ERROR'

    def test_error_code_from_exception_unknown(self):
        exc = RuntimeError('test error')
        result = error_code_from_exception(exc)
        assert result == 'UNKNOWN_ERROR'


@pytest.mark.unit
class TestErrorLogPayload:
    def test_error_log_payload_to_dict(self):
        payload = ErrorLogPayload(
            error_code='CHATBOT_ERROR',
            error_message='something broke',
            context_menu_id=5,
            context_menu_name='suporte',
            context_route='start.suporte',
        )
        result = payload.to_dict()
        assert result == {
            'error_code': 'CHATBOT_ERROR',
            'error_message': 'something broke',
            'context_menu_id': 5,
            'context_menu_name': 'suporte',
            'context_route': 'start.suporte',
        }

    def test_error_log_payload_defaults(self):
        payload = ErrorLogPayload()
        result = payload.to_dict()
        assert result == {
            'error_code': '',
            'error_message': '',
            'context_menu_id': 0,
            'context_menu_name': '',
            'context_route': '',
        }


@pytest.mark.unit
class TestLogEnvelope:
    def test_log_envelope_to_dict(self):
        envelope = LogEnvelope(
            event_id='abc-123',
            event_type=EventType.ERROR,
            timestamp='2025-01-01T00:00:00+00:00',
            session_id=100,
            chat_user_id='user1',
            chat_company_id='company1',
            platform='whatsapp',
            origin='chatgraph:suporte',
            error='something broke',
            payload={'error_code': 'CHATBOT_ERROR', 'error_message': 'boom'},
        )
        result = envelope.to_dict()
        assert result == {
            'event_id': 'abc-123',
            'event_type': 'log_error',
            'event_version': '1.0',
            'timestamp': '2025-01-01T00:00:00+00:00',
            'request_id': '',
            'session_id': 100,
            'chat_user_id': 'user1',
            'chat_company_id': 'company1',
            'platform': 'whatsapp',
            'origin': 'chatgraph:suporte',
            'error': 'something broke',
            'payload': {
                'error_code': 'CHATBOT_ERROR',
                'error_message': 'boom',
            },
        }

    def test_log_envelope_to_json(self):
        envelope = LogEnvelope(
            event_id='abc-123',
            event_type=EventType.ERROR,
            timestamp='2025-01-01T00:00:00+00:00',
        )
        result = envelope.to_json()
        parsed = json.loads(result)
        assert parsed['event_id'] == 'abc-123'
        assert parsed['event_type'] == 'log_error'

    def test_log_envelope_to_dict_empty_payload(self):
        envelope = LogEnvelope(
            event_id='abc-123',
            event_type=EventType.ERROR,
            timestamp='2025-01-01T00:00:00+00:00',
        )
        result = envelope.to_dict()
        assert 'payload' not in result
