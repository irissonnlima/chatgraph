import json
from dataclasses import dataclass, field


class EventType:
    MESSAGE = 'log_message'
    SESSION = 'log_session'
    ROUTE = 'log_route'
    END_ACTION = 'log_end_action'
    ERROR = 'log_error'
    ACK = 'log_ack'


ERROR_CODE_MAP = {
    'ChatbotMessageError': 'CHATBOT_MESSAGE_ERROR',
    'ChatbotError': 'CHATBOT_ERROR',
    'ValueError': 'VALUE_ERROR',
    'TypeError': 'TYPE_ERROR',
    'KeyError': 'KEY_ERROR',
}
_ERROR_CODE_FALLBACK = 'UNKNOWN_ERROR'


def error_code_from_exception(exc: Exception) -> str:
    exc_name = type(exc).__name__
    return ERROR_CODE_MAP.get(exc_name, _ERROR_CODE_FALLBACK)


@dataclass
class ErrorLogPayload:
    error_code: str = ''
    error_message: str = ''
    context_menu_id: int = 0
    context_menu_name: str = ''
    context_route: str = ''

    def to_dict(self) -> dict:
        return {
            'error_code': self.error_code,
            'error_message': self.error_message,
            'context_menu_id': self.context_menu_id,
            'context_menu_name': self.context_menu_name,
            'context_route': self.context_route,
        }


@dataclass
class LogEnvelope:
    event_id: str = ''
    event_type: str = ''
    event_version: str = '1.0'
    timestamp: str = ''
    request_id: str = ''
    session_id: int = 0
    chat_user_id: str = ''
    chat_company_id: str = ''
    platform: str = ''
    origin: str = ''
    error: str = ''
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'event_version': self.event_version,
            'timestamp': self.timestamp,
            'request_id': self.request_id,
            'session_id': self.session_id,
            'chat_user_id': self.chat_user_id,
            'chat_company_id': self.chat_company_id,
            'platform': self.platform,
            'origin': self.origin,
            'error': self.error,
        }
        if self.payload:
            data['payload'] = self.payload
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
