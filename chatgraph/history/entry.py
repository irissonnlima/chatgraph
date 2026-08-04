from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class HistoryRole(Enum):
    USER = 'user'
    BOT = 'bot'
    SYSTEM = 'system'


class HistoryEventType(Enum):
    MESSAGE_IN = 'message_in'
    MESSAGE_OUT = 'message_out'
    ROUTE_CHANGE = 'route_change'
    TRANSFER = 'transfer'
    END_CHAT = 'end_chat'


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

    def to_dict(self) -> dict:
        return {
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
        )
