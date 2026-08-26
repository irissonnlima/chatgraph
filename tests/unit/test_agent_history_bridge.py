"""Testes para a ponte histórico ↔ mensagens do LLM."""

import logging
from datetime import datetime

import pytest

from chatgraph.agent.history_bridge import (
    record_tool_exchange,
    to_agent_messages,
    trim_safe,
)
from chatgraph.agent.types import AgentMessage
from chatgraph.history.entry import (
    HistoryEntry,
    HistoryEventType,
    HistoryRole,
)
from chatgraph.history.store import MemoryHistoryStore


def _entry(
    event_type: HistoryEventType,
    role: HistoryRole = HistoryRole.USER,
    text: str = '',
    key: str = '',
    **overrides,
) -> HistoryEntry:
    message = None
    if text:
        message = {'text_message': {'detail': text}}
    defaults = {
        'idempotency_key': key or f'{event_type.value}-{text}',
        'chat_id': 'u:c',
        'session_id': 1,
        'role': role,
        'event_type': event_type,
        'timestamp': datetime(2026, 1, 1, 12, 0, 0),
        'route': 'start',
        'message': message,
    }
    defaults.update(overrides)
    return HistoryEntry(**defaults)


class _FakeUserCall:
    """Superfície mínima de UserCall usada por record_tool_exchange."""

    def __init__(self, store):
        self._store = store
        self.user_id = 'u1'
        self.company_id = 'c1'
        self.session_id = 7
        self.route = 'start.buscar'
        self.logger = logging.getLogger('test.fake_usercall')

    @property
    def history(self):
        return self._store


@pytest.mark.unit
class TestToAgentMessagesScenario:
    def test_mapeia_roles_e_filtra_eventos_de_navegacao(self):
        entries = [
            _entry(HistoryEventType.MESSAGE_IN, text='oi'),
            _entry(
                HistoryEventType.MESSAGE_OUT,
                role=HistoryRole.BOT,
                text='ola!',
            ),
            _entry(
                HistoryEventType.ROUTE_CHANGE,
                role=HistoryRole.SYSTEM,
                key='rc',
            ),
            _entry(
                HistoryEventType.TRANSFER,
                role=HistoryRole.SYSTEM,
                key='tr',
            ),
            _entry(
                HistoryEventType.END_CHAT,
                role=HistoryRole.SYSTEM,
                key='ec',
            ),
        ]
        messages = to_agent_messages(entries)
        assert [(m.role, m.content) for m in messages] == [
            ('user', 'oi'),
            ('assistant', 'ola!'),
        ]

    def test_filtra_mensagens_vazias_sem_tool_calls(self):
        entries = [
            _entry(HistoryEventType.MESSAGE_IN, key='vazia'),
        ]
        assert to_agent_messages(entries) == []

    def test_tool_call_vira_assistant_com_tool_calls(self):
        entries = [
            _entry(
                HistoryEventType.TOOL_CALL,
                role=HistoryRole.BOT,
                key='tc',
                tool_calls=[
                    {
                        'id': 'call_x_1',
                        'name': 'x',
                        'arguments': '{"a": 1}',
                    },
                ],
            ),
            _entry(
                HistoryEventType.TOOL_RESULT,
                role=HistoryRole.TOOL,
                key='tr2',
                metadata={'content': '{"ok": true}'},
                tool_call_id='call_x_1',
            ),
        ]
        call, result = to_agent_messages(entries)
        assert call.role == 'assistant'
        assert call.content == ''
        assert call.tool_calls[0].id == 'call_x_1'
        assert call.tool_calls[0].arguments == '{"a": 1}'
        assert result.role == 'tool'
        assert result.tool_call_id == 'call_x_1'
        assert result.content == '{"ok": true}'


@pytest.mark.unit
class TestTrimSafeScenario:
    @staticmethod
    def _messages(*roles: str) -> list[AgentMessage]:
        return [
            AgentMessage(role=role, content=f'm{i}')
            for i, role in enumerate(roles)
        ]

    def test_limit_zero_retorna_tudo(self):
        messages = self._messages('user', 'assistant')
        assert trim_safe(messages, 0) == messages

    def test_dentro_do_limite_retorna_tudo(self):
        messages = self._messages('user', 'assistant')
        assert trim_safe(messages, 10) == messages

    def test_corte_simples_sem_tools(self):
        messages = self._messages('user', 'assistant', 'user')
        assert trim_safe(messages, 2) == messages[1:]

    def test_recua_para_incluir_assistant_dona_do_tool(self):
        messages = self._messages(
            'user', 'assistant', 'tool', 'assistant'
        )
        # Janela de 2 começaria no tool (índice 2); recua para incluir
        # a assistant dona (índice 1).
        result = trim_safe(messages, 2)
        assert [m.role for m in result] == ['assistant', 'tool', 'assistant']

    def test_descarta_tools_orfaos_quando_nao_alcanca_a_dona(self):
        roles = ['tool'] * 40 + ['user', 'assistant']
        messages = self._messages(*roles)
        result = trim_safe(messages, 5)
        assert [m.role for m in result] == ['user', 'assistant']


@pytest.mark.unit
class TestRecordToolExchangeScenario:
    @pytest.mark.asyncio
    async def test_grava_par_assistant_tool_pareado(self):
        store = MemoryHistoryStore()
        usercall = _FakeUserCall(store)
        await record_tool_exchange(
            usercall, 'consultar', {'cpf': '123'}, '{"ok": true}'
        )
        entries = await store.get('u1:c1', 7)
        assert len(entries) == 2
        call, result = entries
        assert call.event_type == HistoryEventType.TOOL_CALL
        assert call.role == HistoryRole.BOT
        assert call.tool_calls[0]['name'] == 'consultar'
        assert call.tool_calls[0]['arguments'] == '{"cpf": "123"}'
        assert result.event_type == HistoryEventType.TOOL_RESULT
        assert result.role == HistoryRole.TOOL
        assert result.tool_call_id == call.tool_calls[0]['id']
        assert result.metadata['content'] == '{"ok": true}'

    @pytest.mark.asyncio
    async def test_sem_store_e_noop(self):
        usercall = _FakeUserCall(None)
        await record_tool_exchange(usercall, 'x', None, 'r')

    @pytest.mark.asyncio
    async def test_falha_no_store_nao_propaga(self):
        class _BrokenStore:
            async def record(self, entry):
                raise RuntimeError('boom')

            async def get(self, chat_id, session_id, limit=100):
                return []

            async def clear(self, chat_id, session_id):
                return 0

        usercall = _FakeUserCall(_BrokenStore())
        await record_tool_exchange(usercall, 'x', None, 'r')
