"""A lock keyed by value, with reference-counted table cleanup."""

from __future__ import annotations

import threading
from collections.abc import Hashable, Iterable, Iterator
from contextlib import ExitStack, contextmanager

from ._primitive import Slot
from ._timing import Deadline, check_timeout, ordered, timeout_error


class _Entry(Slot):
    """One key's slot plus the count of threads currently holding or waiting on it."""

    __slots__ = ("refs",)

    def __init__(self, reentrant: bool) -> None:
        super().__init__(reentrant)
        self.refs = 0


class KeyedLock:
    """Serialize work on the same key while letting different keys run in parallel.

    One underlying lock is created per key on first use and discarded once no thread
    is holding or waiting on it, so the table never grows without bound. A single guard
    mutex protects the table itself, which keeps the reference count race-free.

    By default each key uses a non-reentrant lock: a thread that takes a key it already
    holds gets ``RuntimeError`` instead of a deadlock. Pass ``reentrant=True`` to allow
    nesting on the same key. Keys follow ``dict`` rules: ``1``, ``1.0`` and ``True`` are
    the same key. The order in which waiters are woken is not defined, as for
    ``threading.Lock``.
    """

    def __init__(self, *, reentrant: bool = False) -> None:
        self._reentrant = reentrant
        self._guard = threading.Lock()
        self._entries: dict[Hashable, _Entry] = {}

    def _checkout(self, key: Hashable) -> _Entry:
        with self._guard:
            entry = self._entries.get(key)
            if entry is None:
                entry = _Entry(self._reentrant)
                self._entries[key] = entry
            entry.refs += 1
        return entry

    def _checkin(self, key: Hashable, entry: _Entry) -> None:
        with self._guard:
            entry.refs -= 1
            if entry.refs == 0:
                del self._entries[key]

    @contextmanager
    def lock(self, key: Hashable, *, timeout: float | None = None) -> Iterator[None]:
        """Hold the lock for ``key`` for the duration of the ``with`` block.

        ``timeout`` is ``None`` to wait for ever, ``0`` to try once, or a number of
        seconds; ``TimeoutError`` is raised when it runs out.
        """
        limit = check_timeout(timeout)
        entry = self._checkout(key)
        try:
            acquired = entry.acquire(limit)
        except BaseException:
            # Interrupted while waiting (or a re-entry): give the reference back.
            self._checkin(key, entry)
            raise
        if not acquired:
            self._checkin(key, entry)
            raise timeout_error(f"key {key!r}", limit)
        try:
            yield
        finally:
            try:
                entry.release()
            finally:
                self._checkin(key, entry)

    @contextmanager
    def lock_many(
        self, keys: Iterable[Hashable], *, timeout: float | None = None
    ) -> Iterator[None]:
        """Hold the locks for every key in ``keys`` for the duration of the ``with`` block.

        Keys are deduplicated and taken in sorted order, so two callers locking the same
        keys can never deadlock each other; they must therefore be mutually sortable.
        ``timeout`` bounds the whole acquisition. On failure nothing stays locked.
        """
        deadline = Deadline(check_timeout(timeout))
        with ExitStack() as stack:
            for key in ordered(keys):
                stack.enter_context(self.lock(key, timeout=deadline.remaining()))
            yield

    def active_keys(self) -> int:
        """Number of keys currently held or waited on. Zero when fully idle."""
        with self._guard:
            return len(self._entries)
