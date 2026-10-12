"""A keyed lock backed by a fixed pool of stripes, so memory stays bounded."""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable, Iterator
from contextlib import ExitStack, contextmanager

from ._primitive import Slot
from ._timing import Deadline, check_timeout, ordered, timeout_error


class StripedLock:
    """Map keys onto a fixed number of locks, capping memory at the cost of collisions.

    Unlike :class:`KeyedLock`, the lock count never changes: two unrelated keys can share
    a stripe and so block each other (false contention), but the table is allocated once
    and never grows. Reach for this when the key space is unbounded or very large and a
    rare spurious wait is cheaper than per-key bookkeeping.

    Because unrelated keys can share a stripe, nesting ``lock(a)`` inside ``lock(b)`` on
    one thread may hit the same stripe twice. With the default non-reentrant stripes that
    raises ``RuntimeError`` instead of deadlocking; use :meth:`lock_many` to hold several
    keys at once.
    """

    def __init__(self, stripes: int = 64, *, reentrant: bool = False) -> None:
        if isinstance(stripes, bool) or not isinstance(stripes, int):
            raise TypeError(f"stripes must be an int, not {type(stripes).__name__}")
        if stripes < 1:
            raise ValueError("stripes must be at least 1")
        self._slots = [Slot(reentrant) for _ in range(stripes)]

    @property
    def stripes(self) -> int:
        """The fixed number of underlying locks."""
        return len(self._slots)

    def _stripe_for(self, key: Hashable) -> int:
        return hash(key) % len(self._slots)

    @contextmanager
    def _hold(self, index: int, limit: float | None, what: Callable[[], str]) -> Iterator[None]:
        slot = self._slots[index]
        if not slot.acquire(limit):
            raise timeout_error(what(), limit)
        try:
            yield
        finally:
            slot.release()

    @contextmanager
    def lock(self, key: Hashable, *, timeout: float | None = None) -> Iterator[None]:
        """Hold the stripe backing ``key`` for the duration of the ``with`` block.

        ``timeout`` is ``None`` to wait for ever, ``0`` to try once, or a number of
        seconds; ``TimeoutError`` is raised when it runs out.
        """
        limit = check_timeout(timeout)
        with self._hold(self._stripe_for(key), limit, lambda: f"key {key!r}"):
            yield

    @contextmanager
    def lock_many(
        self, keys: Iterable[Hashable], *, timeout: float | None = None
    ) -> Iterator[None]:
        """Hold the stripes backing every key in ``keys`` for the ``with`` block.

        Each stripe is taken once, in index order, so callers can never deadlock each
        other and keys sharing a stripe are fine. ``timeout`` bounds the whole
        acquisition. On failure nothing stays locked.
        """
        if isinstance(keys, (str, bytes)):
            raise TypeError("keys must be a collection of keys, not a single str or bytes")
        deadline = Deadline(check_timeout(timeout))
        stripes = ordered(self._stripe_for(key) for key in keys)
        with ExitStack() as stack:
            for index in stripes:
                what = f"stripe {index}".__str__
                stack.enter_context(self._hold(index, deadline.remaining(), what))
            yield
