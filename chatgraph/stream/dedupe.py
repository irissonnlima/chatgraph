from collections import OrderedDict


class LRU:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._items: OrderedDict[str, None] = OrderedDict()

    def seen(self, key: str) -> bool:
        if key not in self._items:
            return False
        self._items.move_to_end(key)
        return True

    def add(self, key: str) -> None:
        self._items[key] = None
        self._items.move_to_end(key)
        while len(self._items) > self._capacity:
            self._items.popitem(last=False)
