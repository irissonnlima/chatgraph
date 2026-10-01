# ruff: noqa: PLR6301 - testes em classe e literais nos asserts, como no
# resto da suíte.
import pytest

from chatgraph.stream.dedupe import LRU


@pytest.mark.unit
class TestLRU:
    def test_seen_after_add(self):
        lru = LRU(2)

        assert not lru.seen('a:rh')
        lru.add('a:rh')

        assert lru.seen('a:rh')

    def test_capacity_evicts_oldest(self):
        lru = LRU(2)
        for key in ('a', 'b', 'c'):
            lru.add(key)

        assert not lru.seen('a')
        assert lru.seen('b')
        assert lru.seen('c')

    def test_seen_promotes_entry(self):
        lru = LRU(2)
        lru.add('a')
        lru.add('b')
        assert lru.seen('a')
        lru.add('c')

        assert lru.seen('a')
        assert not lru.seen('b')

    def test_same_msg_id_with_different_menus_does_not_collide(self):
        lru = LRU(4)
        lru.add('m1:rh')

        assert lru.seen('m1:rh')
        assert not lru.seen('m1:geral')
