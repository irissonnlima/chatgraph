from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class HistoryRole(Enum):
    USER = 'user'
    BOT = 'bot'
    SYSTEM = 'system'
    TOOL = 'tool'


class HistoryEventType(Enum):
    MESSAGE_IN = 'message_in'
    MESSAGE_OUT = 'message_out'
    ROUTE_CHANGE = 'route_change'
    TRANSFER = 'transfer'
    END_CHAT = 'end_chat'
    TOOL_CALL = 'tool_call'
    TOOL_RESULT = 'tool_result'


@dataclass
class HistoryEntry:
    idempotency_key: str
    chat_id: str
    session_id: Optional[int]
    role: HistoryRole
    event_type: HistoryEventType
    timestamp: datetime
    route: str
    message: Optional[dict] = None
    metadata: dict = field(default_factory=dict)
    # Tool exchange (agentes de IA): tool_calls na mensagem assistant e
    # tool_call_id na mensagem de resultado. A API do LLM exige o par.
    tool_calls: Optional[list[dict]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> dict:
        data = {
            'idempotency_key': self.idempotency_key,
            'chat_id': self.chat_id,
            'session_id': self.session_id,
            'role': self.role.value,
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'route': self.route,
            'message': self.message,
            'metadata': self.metadata,
        }
        if self.tool_calls is not None:
            data['tool_calls'] = self.tool_calls
        if self.tool_call_id is not None:
            data['tool_call_id'] = self.tool_call_id
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'HistoryEntry':
        return cls(
            idempotency_key=data['idempotency_key'],
            chat_id=data['chat_id'],
            session_id=data.get('session_id'),
            role=HistoryRole(data['role']),
            event_type=HistoryEventType(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            route=data['route'],
            message=data.get('message'),
            metadata=data.get('metadata', {}),
            tool_calls=data.get('tool_calls'),
            tool_call_id=data.get('tool_call_id'),
        )
