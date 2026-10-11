"""A lock keyed by value, with reference-counted table cleanup."""

from __future__ import annotations

import threading
from collections.abc import Hashable, Iterator
from contextlib import contextmanager

from ._primitive import LockPrimitive, lock_factory


class _Entry:
    """One key's lock plus the count of threads currently referencing it."""

    __slots__ = ("lock", "refs")

    def __init__(self, lock: LockPrimitive) -> None:
        self.lock = lock
        self.refs = 0


class KeyedLock:
    """Serialize work on the same key while letting different keys run in parallel.

    One underlying lock is created per key on first use and discarded once no thread
    is holding or waiting on it, so the table never grows without bound. A single guard
    mutex protects the table itself, which keeps the reference count race-free.

    By default each key uses a non-reentrant lock: a thread that re-enters ``lock`` on
    a key it already holds deadlocks. Pass ``reentrant=True`` for per-key reentrancy.
    """

    def __init__(self, *, reentrant: bool = False) -> None:
        self._make_lock = lock_factory(reentrant)
        self._guard = threading.Lock()
        self._entries: dict[Hashable, _Entry] = {}

    def _checkout(self, key: Hashable) -> _Entry:
        with self._guard:
            entry = self._entries.get(key)
            if entry is None:
                entry = _Entry(self._make_lock())
                self._entries[key] = entry
            entry.refs += 1
        return entry

    def _checkin(self, key: Hashable, entry: _Entry) -> None:
        with self._guard:
            entry.refs -= 1
            if entry.refs == 0:
                del self._entries[key]

    @contextmanager
    def lock(self, key: Hashable) -> Iterator[None]:
        """Hold the lock for ``key`` for the duration of the ``with`` block."""
        entry = self._checkout(key)
        entry.lock.acquire()
        try:
            yield
        finally:
            entry.lock.release()
            self._checkin(key, entry)

    def active_keys(self) -> int:
        """Number of keys currently held or waited on. Zero when fully idle."""
        with self._guard:
            return len(self._entries)
