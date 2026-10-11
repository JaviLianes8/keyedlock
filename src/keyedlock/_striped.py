"""A keyed lock backed by a fixed pool of stripes, so memory stays bounded."""

from __future__ import annotations

from collections.abc import Hashable, Iterator
from contextlib import contextmanager

from ._primitive import lock_factory


class StripedLock:
    """Map keys onto a fixed number of locks, capping memory at the cost of collisions.

    Unlike :class:`KeyedLock`, the lock count never changes: two unrelated keys can share
    a stripe and so block each other (false contention), but the table is allocated once
    and never grows. Reach for this when the key space is unbounded or very large and a
    rare spurious wait is cheaper than per-key bookkeeping.
    """

    def __init__(self, stripes: int = 64, *, reentrant: bool = False) -> None:
        if stripes < 1:
            raise ValueError("stripes must be at least 1")
        make_lock = lock_factory(reentrant)
        self._locks = [make_lock() for _ in range(stripes)]

    @property
    def stripes(self) -> int:
        """The fixed number of underlying locks."""
        return len(self._locks)

    def _stripe_for(self, key: Hashable) -> int:
        return hash(key) % len(self._locks)

    @contextmanager
    def lock(self, key: Hashable) -> Iterator[None]:
        """Hold the stripe backing ``key`` for the duration of the ``with`` block."""
        primitive = self._locks[self._stripe_for(key)]
        primitive.acquire()
        try:
            yield
        finally:
            primitive.release()
