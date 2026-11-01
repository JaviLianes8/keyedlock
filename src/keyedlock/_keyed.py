"""A lock keyed by value, with reference-counted table cleanup."""

from __future__ import annotations

import threading
from collections.abc import Hashable, Iterable, Iterator
from contextlib import ExitStack, contextmanager

from ._primitive import Slot
from ._table import KeyTable
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

    >>> from keyedlock import KeyedLock
    >>> locks = KeyedLock(reentrant=True)
    >>> with locks.lock("job"), locks.lock("job"):
    ...     print(locks.active_keys())
    1
    >>> locks.active_keys()
    0
    """

    def __init__(self, *, reentrant: bool = False) -> None:
        if not isinstance(reentrant, bool):
            raise TypeError("reentrant must be a bool")
        self._reentrant = reentrant
        self._guard = threading.Lock()
        self._entries: KeyTable[Hashable, _Entry] = KeyTable()

    def _checkout(self, key: Hashable) -> _Entry:
        with self._guard:
            entry = self._entries.intern(key, lambda _: _Entry(self._reentrant))
            entry.refs += 1
        return entry

    def _checkin(self, key: Hashable, entry: _Entry) -> None:
        with self._guard:
            entry.refs -= 1
            if entry.refs == 0:
                self._entries.drop(entry)

    @contextmanager
    def _hold(self, key: Hashable, limit: float | None, shown: float | None) -> Iterator[None]:
        entry = self._checkout(key)
        held = False
        try:
            held = entry.acquire(limit)
            if not held:
                raise timeout_error("key", shown)
            yield
        finally:
            # Runs on success, timeout, re-entry and an interrupted wait alike.
            try:
                if held:
                    entry.release()
            finally:
                self._checkin(key, entry)

    @contextmanager
    def lock(self, key: Hashable, *, timeout: float | None = None) -> Iterator[None]:
        """Hold the lock for ``key`` for the duration of the ``with`` block.

        ``timeout`` is ``None`` to wait for ever, ``0`` to try once, or a number of
        seconds; ``TimeoutError`` is raised when it runs out.

        >>> from keyedlock import KeyedLock
        >>> with KeyedLock().lock("job", timeout=0) as held:
        ...     print(held)
        None
        """
        limit = check_timeout(timeout)
        with self._hold(key, limit, limit):
            yield

    @contextmanager
    def lock_many(
        self, keys: Iterable[Hashable], *, timeout: float | None = None
    ) -> Iterator[None]:
        """Hold the locks for every key in ``keys`` for the duration of the ``with`` block.

        Keys are deduplicated and taken in sorted order, preventing cycles between
        unnested groups on this instance. They need a total order (all ``str``, all
        ``int``, ...). ``timeout`` bounds acquisition waits, not the body or user key
        operations. On failure nothing acquired by this call stays locked.

        >>> from keyedlock import KeyedLock
        >>> locks = KeyedLock()
        >>> with locks.lock_many(["b", "a", "a"]):
        ...     print(locks.active_keys())
        2
        """
        limit = check_timeout(timeout)
        deadline = Deadline(limit)
        with ExitStack() as stack:
            for key in ordered(keys):
                stack.enter_context(self._hold(key, deadline.remaining(), limit))
            yield

    def active_keys(self) -> int:
        """Number of keys currently held or waited on. Zero when fully idle.

        >>> from keyedlock import KeyedLock
        >>> KeyedLock().active_keys()
        0
        """
        with self._guard:
            return len(self._entries)
