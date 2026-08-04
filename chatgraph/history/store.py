from typing import Optional, Protocol

from .entry import HistoryEntry


class HistoryStore(Protocol):
    async def record(self, entry: HistoryEntry) -> bool:
        """Registra entry. Retorna False se duplicada."""
        ...

    async def get(
        self,
        chat_id: str,
        session_id: Optional[int],
        limit: int = 100,
    ) -> list[HistoryEntry]:
        """Retorna entradas ordenadas por timestamp crescente."""
        ...

    async def clear(self, chat_id: str, session_id: Optional[int]) -> int:
        """Remove todas as entradas da chave. Retorna count removido."""
        ...


class MemoryHistoryStore:
    """Implementação em memória de HistoryStore."""

    def __init__(self, max_entries_per_key: int = 1000) -> None:
        self._max_entries_per_key = max_entries_per_key
        self._store: dict[
            tuple[str, Optional[int]],
            dict[str, HistoryEntry],
        ] = {}

    async def record(self, entry: HistoryEntry) -> bool:
        key = (entry.chat_id, entry.session_id)
        bucket = self._store.setdefault(key, {})
        if entry.idempotency_key in bucket:
            return False
        bucket[entry.idempotency_key] = entry
        if len(bucket) > self._max_entries_per_key:
            oldest_key = min(
                bucket,
                key=lambda k: bucket[k].timestamp,
            )
            del bucket[oldest_key]
        return True

    async def get(
        self,
        chat_id: str,
        session_id: Optional[int],
        limit: int = 100,
    ) -> list[HistoryEntry]:
        bucket = self._store.get((chat_id, session_id), {})
        ordered = sorted(bucket.values(), key=lambda e: e.timestamp)
        return ordered[-limit:]

    async def clear(self, chat_id: str, session_id: Optional[int]) -> int:
        key = (chat_id, session_id)
        bucket = self._store.pop(key, {})
        return len(bucket)
