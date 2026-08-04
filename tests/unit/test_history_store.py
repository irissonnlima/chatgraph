"""Testes para o módulo de histórico (HistoryEntry, keys, MemoryStore)."""

from datetime import datetime

import pytest

from chatgraph.history.entry import (
    HistoryEntry,
    HistoryEventType,
    HistoryRole,
)
from chatgraph.history.keys import generate_idempotency_key
from chatgraph.history.store import MemoryHistoryStore


def _make_entry(
    idempotency_key: str = 'key-1',
    chat_id: str = 'user1:company1',
    session_id: int | None = 1,
    role: HistoryRole = HistoryRole.USER,
    event_type: HistoryEventType = HistoryEventType.MESSAGE_IN,
    timestamp: datetime | None = None,
    route: str = 'start',
    message: dict | None = None,
    metadata: dict | None = None,
) -> HistoryEntry:
    return HistoryEntry(
        idempotency_key=idempotency_key,
        chat_id=chat_id,
        session_id=session_id,
        role=role,
        event_type=event_type,
        timestamp=timestamp or datetime.now(),
        route=route,
        message=message,
        metadata=metadata or {},
    )


@pytest.mark.unit
class TestMemoryHistoryStore:
    """Testes para MemoryHistoryStore."""

    @pytest.mark.asyncio
    async def test_t1_record_returns_true_for_new_entry(self):
        store = MemoryHistoryStore()
        entry = _make_entry(idempotency_key='k1')

        result = await store.record(entry)

        assert result is True

    @pytest.mark.asyncio
    async def test_t2_record_returns_false_for_duplicate_idempotency_key(
        self,
    ):
        store = MemoryHistoryStore()
        entry = _make_entry(
            idempotency_key='dup', timestamp=datetime(2024, 1, 1)
        )
        await store.record(entry)
        duplicate = _make_entry(
            idempotency_key='dup', timestamp=datetime(2024, 1, 2)
        )

        result = await store.record(duplicate)

        assert result is False
        entries = await store.get('user1:company1', 1)
        assert len(entries) == 1

    @pytest.mark.asyncio
    async def test_t3_get_returns_entries_ordered_by_timestamp(self):
        store = MemoryHistoryStore()
        e1 = _make_entry(idempotency_key='a', timestamp=datetime(2024, 1, 3))
        e2 = _make_entry(idempotency_key='b', timestamp=datetime(2024, 1, 1))
        e3 = _make_entry(idempotency_key='c', timestamp=datetime(2024, 1, 2))
        for e in (e1, e2, e3):
            await store.record(e)

        entries = await store.get('user1:company1', 1)

        assert [e.idempotency_key for e in entries] == ['b', 'c', 'a']

    @pytest.mark.asyncio
    async def test_t4_get_respects_limit(self):
        store = MemoryHistoryStore()
        for i in range(5):
            await store.record(
                _make_entry(
                    idempotency_key=f'k{i}',
                    timestamp=datetime(2024, 1, 1 + i),
                )
            )

        entries = await store.get('user1:company1', 1, limit=2)

        assert len(entries) == 2
        assert [e.idempotency_key for e in entries] == ['k3', 'k4']

    @pytest.mark.asyncio
    async def test_t5_clear_removes_entries_and_returns_count(self):
        store = MemoryHistoryStore()
        for i in range(3):
            await store.record(_make_entry(idempotency_key=f'k{i}'))

        count = await store.clear('user1:company1', 1)

        assert count == 3
        entries = await store.get('user1:company1', 1)
        assert entries == []

    @pytest.mark.asyncio
    async def test_t6_record_evicts_oldest_when_max_entries_exceeded(
        self,
    ):
        store = MemoryHistoryStore(max_entries_per_key=2)
        e1 = _make_entry(
            idempotency_key='old',
            timestamp=datetime(2024, 1, 1),
        )
        e2 = _make_entry(
            idempotency_key='mid',
            timestamp=datetime(2024, 1, 2),
        )
        await store.record(e1)
        await store.record(e2)
        e3 = _make_entry(
            idempotency_key='new',
            timestamp=datetime(2024, 1, 3),
        )

        await store.record(e3)

        entries = await store.get('user1:company1', 1, limit=100)
        keys = {e.idempotency_key for e in entries}
        assert keys == {'mid', 'new'}
        assert 'old' not in keys

    @pytest.mark.asyncio
    async def test_t7_get_returns_empty_list_for_unknown_key(self):
        store = MemoryHistoryStore()

        entries = await store.get('nobody:nowhere', None)

        assert entries == []

    @pytest.mark.asyncio
    async def test_t8_clear_returns_zero_for_unknown_key(self):
        store = MemoryHistoryStore()

        count = await store.clear('nobody:nowhere', None)

        assert count == 0


@pytest.mark.unit
class TestHistoryEntrySerialization:
    """Testes de serialização do HistoryEntry."""

    def test_t9_history_entry_to_dict_and_from_dict_roundtrip(self):
        entry = _make_entry(
            idempotency_key='abc',
            chat_id='u:c',
            session_id=42,
            role=HistoryRole.BOT,
            event_type=HistoryEventType.MESSAGE_OUT,
            timestamp=datetime(2024, 5, 10, 12, 30, 45),
            route='start.menu',
            message={'text': 'oi'},
            metadata={'foo': 'bar'},
        )

        data = entry.to_dict()
        restored = HistoryEntry.from_dict(data)

        assert restored.idempotency_key == 'abc'
        assert restored.chat_id == 'u:c'
        assert restored.session_id == 42
        assert restored.role is HistoryRole.BOT
        assert restored.event_type is HistoryEventType.MESSAGE_OUT
        assert restored.timestamp == datetime(2024, 5, 10, 12, 30, 45)
        assert restored.route == 'start.menu'
        assert restored.message == {'text': 'oi'}
        assert restored.metadata == {'foo': 'bar'}

    def test_t10_history_entry_with_none_message_serializes_correctly(
        self,
    ):
        entry = _make_entry(
            event_type=HistoryEventType.ROUTE_CHANGE,
            role=HistoryRole.SYSTEM,
            message=None,
        )

        data = entry.to_dict()
        restored = HistoryEntry.from_dict(data)

        assert data['message'] is None
        assert restored.message is None

    def test_t11_history_entry_with_none_session_id_serializes_correctly(
        self,
    ):
        entry = _make_entry(session_id=None)

        data = entry.to_dict()
        restored = HistoryEntry.from_dict(data)

        assert data['session_id'] is None
        assert restored.session_id is None


@pytest.mark.unit
class TestGenerateIdempotencyKey:
    """Testes para generate_idempotency_key."""

    def test_t12_generate_idempotency_key_is_deterministic(self):
        args = (
            'u:c',
            1,
            HistoryRole.USER.value,
            HistoryEventType.MESSAGE_IN.value,
            'start',
            '{"text": "oi"}',
        )

        k1 = generate_idempotency_key(*args)
        k2 = generate_idempotency_key(*args)

        assert k1 == k2
        assert len(k1) == 64

    def test_t13_generate_idempotency_key_differs_for_different_role(
        self,
    ):
        base = (
            'u:c',
            1,
            HistoryRole.USER.value,
            HistoryEventType.MESSAGE_IN.value,
            'start',
            '',
        )
        k_user = generate_idempotency_key(*base)
        bot_args = (
            'u:c',
            1,
            HistoryRole.BOT.value,
            HistoryEventType.MESSAGE_IN.value,
            'start',
            '',
        )
        k_bot = generate_idempotency_key(*bot_args)

        assert k_user != k_bot

    def test_t14_generate_idempotency_key_handles_none_session_id(
        self,
    ):
        k_none = generate_idempotency_key(
            'u:c',
            None,
            HistoryRole.USER.value,
            HistoryEventType.MESSAGE_IN.value,
            'start',
            '',
        )
        k_str_none = generate_idempotency_key(
            'u:c',
            'None',
            HistoryRole.USER.value,
            HistoryEventType.MESSAGE_IN.value,
            'start',
            '',
        )

        assert k_none == k_str_none
