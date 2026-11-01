"""The asyncio counterpart of ``KeyedLock``: fair per key and safe under cancellation."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Hashable, Iterable
from contextlib import AsyncExitStack, asynccontextmanager

from ._fifo import FifoLock
from ._primitive import drop_entry
from ._timing import Deadline, check_timeout, checked_key, ordered, timeout_error


class _AsyncEntry:
    """One key's lock, its holder task and its holder-plus-waiter count."""

    __slots__ = ("lock", "owner", "refs")

    def __init__(self) -> None:
        self.lock = FifoLock()
        self.owner: asyncio.Task[object] | None = None
        self.refs = 0


class AsyncKeyedLock:
    """Serialize coroutines on the same key while different keys run concurrently.

    Each key gets a lock on first use, dropped once no task holds or waits on it.
    Waiters on one key, with or without a timeout, are served first come, first served.
    A task cancelled or timed out while waiting leaves nothing behind. Like
    ``asyncio.Lock`` it is not thread-safe: use one instance from one event loop.

    Locks are not reentrant: a task that takes a key it already holds gets
    ``RuntimeError`` instead of waiting on itself for ever.

    >>> import asyncio
    >>> from keyedlock import AsyncKeyedLock
    >>> async def example():
    ...     locks = AsyncKeyedLock()
    ...     async with locks.lock("job"):
    ...         print(locks.active_keys())
    ...     print(locks.active_keys())
    >>> asyncio.run(example())
    1
    0
    """

    def __init__(self) -> None:
        self._entries: dict[Hashable, _AsyncEntry] = {}

    def _checkout(self, key: Hashable) -> _AsyncEntry:
        checked_key(key)
        entry = self._entries.get(key)
        if entry is None:
            entry = self._entries[key] = _AsyncEntry()
        entry.refs += 1
        return entry

    def _checkin(self, key: Hashable, entry: _AsyncEntry) -> None:
        entry.refs -= 1
        if entry.refs == 0:
            drop_entry(self._entries, key, entry)

    @asynccontextmanager
    async def _hold(
        self, key: Hashable, limit: float | None, shown: float | None
    ) -> AsyncIterator[None]:
        entry = self._checkout(key)
        held = False
        try:
            task = asyncio.current_task()
            if task is not None and entry.owner is task:
                raise RuntimeError(
                    "this task already holds the lock; taking it again would deadlock"
                )
            held = await entry.lock.acquire(limit)
            if not held:
                raise timeout_error("key", shown)
            entry.owner = task
            yield
        finally:
            try:
                if held:
                    entry.owner = None
                    entry.lock.release()
            finally:
                self._checkin(key, entry)

    @asynccontextmanager
    async def lock(self, key: Hashable, *, timeout: float | None = None) -> AsyncIterator[None]:
        """Hold the lock for ``key`` for the duration of the ``async with`` block.

        ``timeout`` is ``None`` to wait for ever, ``0`` to try once, or a number of
        seconds; ``TimeoutError`` is raised when it runs out.

        >>> import asyncio
        >>> from keyedlock import AsyncKeyedLock
        >>> async def example():
        ...     async with AsyncKeyedLock().lock("job", timeout=0) as held:
        ...         print(held)
        >>> asyncio.run(example())
        None
        """
        limit = check_timeout(timeout)
        async with self._hold(key, limit, limit):
            yield

    @asynccontextmanager
    async def lock_many(
        self, keys: Iterable[Hashable], *, timeout: float | None = None
    ) -> AsyncIterator[None]:
        """Hold the locks for every key in ``keys`` for the ``async with`` block.

        Keys are deduplicated and taken in sorted order, so they need a total order.
        ``timeout`` bounds the whole acquisition. On failure nothing stays locked.

        >>> import asyncio
        >>> from keyedlock import AsyncKeyedLock
        >>> async def example():
        ...     locks = AsyncKeyedLock()
        ...     async with locks.lock_many(["b", "a", "a"]):
        ...         print(locks.active_keys())
        >>> asyncio.run(example())
        2
        """
        limit = check_timeout(timeout)
        deadline = Deadline(limit)
        async with AsyncExitStack() as stack:
            for key in ordered(keys):
                await stack.enter_async_context(self._hold(key, deadline.remaining(), limit))
            yield

    def active_keys(self) -> int:
        """Number of keys currently held or waited on. Zero when fully idle.

        >>> from keyedlock import AsyncKeyedLock
        >>> AsyncKeyedLock().active_keys()
        0
        """
        return len(self._entries)
