"""Dictionary-equivalent key storage with bounded hash collision buckets."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterator
from typing import Generic, TypeVar

from ._keys import checked_hash

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class KeyTable(Generic[K, V]):
    def __init__(self) -> None:
        self._buckets: dict[int, list[tuple[K, V]]] = {}
        self._locations: dict[int, int] = {}

    def intern(self, key: K, create: Callable[[K], V]) -> V:
        code = checked_hash(key)
        bucket = self._buckets.get(code)
        if bucket is not None:
            for stored, value in bucket:
                if stored is key or stored == key:
                    return value
            if len(bucket) >= 64:
                raise ValueError("key hash collision limit exceeded (64)")
        value = create(key)
        if bucket is None:
            bucket = self._buckets[code] = []
        bucket.append((key, value))
        self._locations[id(value)] = code
        return value

    def drop(self, value: V) -> None:
        # Identity removal neither rehashes mutated keys nor compares unrelated keys.
        code = self._locations.pop(id(value))
        bucket = self._buckets[code]
        for index, (_, stored) in enumerate(bucket):
            if stored is value:
                del bucket[index]
                break
        if not bucket:
            del self._buckets[code]

    def values(self) -> Iterator[V]:
        for bucket in self._buckets.values():
            for _, value in bucket:
                yield value

    def __len__(self) -> int:
        return len(self._locations)
