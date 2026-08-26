"""Testes para os campos de tool exchange no HistoryEntry."""

from datetime import datetime

import pytest

from chatgraph.history.entry import (
    HistoryEntry,
    HistoryEventType,
    HistoryRole,
)


def _make_entry(**overrides) -> HistoryEntry:
    defaults = {
        'idempotency_key': 'key-1',
        'chat_id': 'user1:company1',
        'session_id': 1,
        'role': HistoryRole.BOT,
        'event_type': HistoryEventType.TOOL_CALL,
        'timestamp': datetime(2026, 1, 1, 12, 0, 0),
        'route': 'start',
    }
    defaults.update(overrides)
    return HistoryEntry(**defaults)


@pytest.mark.unit
class TestToolEntryEnumsScenario:
    def test_role_tool_existe(self):
        assert HistoryRole.TOOL.value == 'tool'

    def test_event_types_de_tool_existem(self):
        assert HistoryEventType.TOOL_CALL.value == 'tool_call'
        assert HistoryEventType.TOOL_RESULT.value == 'tool_result'


@pytest.mark.unit
class TestToolEntryRoundTripScenario:
    def test_round_trip_com_tool_calls(self):
        entry = _make_entry(
            tool_calls=[
                {'id': 'call_x_1', 'name': 'x', 'arguments': '{}'},
            ],
        )
        data = entry.to_dict()
        assert data['tool_calls'] == entry.tool_calls
        restored = HistoryEntry.from_dict(data)
        assert restored.tool_calls == entry.tool_calls
        assert restored.tool_call_id is None

    def test_round_trip_com_tool_call_id(self):
        entry = _make_entry(
            role=HistoryRole.TOOL,
            event_type=HistoryEventType.TOOL_RESULT,
            metadata={'content': '{"status": "ok"}'},
            tool_call_id='call_x_1',
        )
        data = entry.to_dict()
        assert data['tool_call_id'] == 'call_x_1'
        restored = HistoryEntry.from_dict(data)
        assert restored.tool_call_id == 'call_x_1'
        assert restored.metadata == {'content': '{"status": "ok"}'}

    def test_to_dict_omite_campos_de_tool_quando_ausentes(self):
        entry = _make_entry(
            role=HistoryRole.USER,
            event_type=HistoryEventType.MESSAGE_IN,
        )
        data = entry.to_dict()
        assert 'tool_calls' not in data
        assert 'tool_call_id' not in data

    def test_from_dict_aceita_dados_antigos_sem_campos_de_tool(self):
        data = {
            'idempotency_key': 'key-antiga',
            'chat_id': 'u:c',
            'session_id': None,
            'role': 'user',
            'event_type': 'message_in',
            'timestamp': '2026-01-01T12:00:00',
            'route': 'start',
            'message': None,
            'metadata': {},
        }
        restored = HistoryEntry.from_dict(data)
        assert restored.tool_calls is None
        assert restored.tool_call_id is None
