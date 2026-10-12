"""The asyncio counterpart of ``KeyedLock``: fair per key and safe under cancellation."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Hashable, Iterable
from contextlib import AsyncExitStack, asynccontextmanager
from typing import Any

from ._timing import Deadline, check_timeout, ordered, timeout_error


class _AsyncEntry:
    """One key's asyncio lock, its holder task and its holder-plus-waiter count."""

    __slots__ = ("lock", "owner", "refs")

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.owner: asyncio.Task[object] | None = None
        self.refs = 0


def _abandon(attempt: asyncio.Future[Any], lock: asyncio.Lock) -> None:
    """Cancel an acquisition we gave up on, releasing the lock if it won the race."""

    def undo(future: asyncio.Future[Any]) -> None:
        if not future.cancelled() and future.exception() is None:
            lock.release()

    attempt.cancel()
    attempt.add_done_callback(undo)


async def _acquire_within(lock: asyncio.Lock, timeout: float) -> bool:
    attempt = asyncio.ensure_future(lock.acquire())
    try:
        done, _ = await asyncio.wait({attempt}, timeout=timeout)
    except BaseException:
        _abandon(attempt, lock)
        raise
    if not done:
        _abandon(attempt, lock)
        return False
    return attempt.result()


class AsyncKeyedLock:
    """Serialize coroutines on the same key while different keys run concurrently.

    Each key gets an ``asyncio.Lock`` on first use, dropped once no task holds or waits
    on it. Waiters on one key are served first come, first served. A task cancelled or
    timed out while waiting leaves nothing behind. Like ``asyncio.Lock`` it is not
    thread-safe: use one instance from one event loop.

    Locks are not reentrant: a task that takes a key it already holds gets
    ``RuntimeError`` instead of waiting on itself for ever.
    """

    def __init__(self) -> None:
        self._entries: dict[Hashable, _AsyncEntry] = {}

    def _checkout(self, key: Hashable) -> _AsyncEntry:
        entry = self._entries.get(key)
        if entry is None:
            entry = self._entries[key] = _AsyncEntry()
        entry.refs += 1
        return entry

    def _checkin(self, key: Hashable, entry: _AsyncEntry) -> None:
        entry.refs -= 1
        if entry.refs == 0:
            del self._entries[key]

    async def _acquire(self, entry: _AsyncEntry, limit: float | None) -> bool:
        task = asyncio.current_task()
        if task is not None and entry.owner is task:
            raise RuntimeError("this task already holds the lock; taking it again would deadlock")
        if limit is None or (entry.refs == 1 and not entry.lock.locked()):
            # Nobody else holds or waits on this key, so acquire() returns at once (at
            # worst after one loop turn, if an abandoned attempt is still unwinding).
            await entry.lock.acquire()
        elif not await _acquire_within(entry.lock, limit):
            return False
        entry.owner = task
        return True

    @asynccontextmanager
    async def lock(self, key: Hashable, *, timeout: float | None = None) -> AsyncIterator[None]:
        """Hold the lock for ``key`` for the duration of the ``async with`` block.

        ``timeout`` is ``None`` to wait for ever, ``0`` to try once, or a number of
        seconds; ``TimeoutError`` is raised when it runs out.
        """
        limit = check_timeout(timeout)
        entry = self._checkout(key)
        try:
            acquired = await self._acquire(entry, limit)
        except BaseException:
            self._checkin(key, entry)
            raise
        if not acquired:
            self._checkin(key, entry)
            raise timeout_error(f"key {key!r}", limit)
        try:
            yield
        finally:
            entry.owner = None
            entry.lock.release()
            self._checkin(key, entry)

    @asynccontextmanager
    async def lock_many(
        self, keys: Iterable[Hashable], *, timeout: float | None = None
    ) -> AsyncIterator[None]:
        """Hold the locks for every key in ``keys`` for the ``async with`` block.

        Keys are deduplicated and taken in sorted order, so they must be mutually
        sortable. ``timeout`` bounds the whole acquisition. On failure nothing stays locked.
        """
        deadline = Deadline(check_timeout(timeout))
        async with AsyncExitStack() as stack:
            for key in ordered(keys):
                await stack.enter_async_context(self.lock(key, timeout=deadline.remaining()))
            yield

    def active_keys(self) -> int:
        """Number of keys currently held or waited on. Zero when fully idle."""
        return len(self._entries)
