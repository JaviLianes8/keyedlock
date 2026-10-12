"""The per-key slot shared by the keyed and striped locks: a primitive plus its owner."""

from __future__ import annotations

import threading
from collections.abc import Hashable
from typing import Protocol, TypeVar

E = TypeVar("E")


class LockPrimitive(Protocol):
    """A blocking lock with the ``threading.Lock`` acquire signature."""

    def acquire(self, blocking: bool = ..., timeout: float = ...) -> bool: ...

    def release(self) -> None: ...


class Slot:
    """One lock and, when it is not reentrant, the thread that holds it.

    Tracking the owner turns a same-thread re-entry, which would block on itself for
    ever, into an immediate ``RuntimeError``. Only the holder writes ``owner``, so a
    thread that reads its own ident there really does hold the lock.
    """

    __slots__ = ("lock", "owner", "reentrant")

    def __init__(self, reentrant: bool) -> None:
        self.lock: LockPrimitive = threading.RLock() if reentrant else threading.Lock()
        self.owner: int | None = None
        self.reentrant = reentrant

    def acquire(self, timeout: float | None) -> bool:
        """Take the lock, waiting at most ``timeout`` seconds (``None`` waits for ever)."""
        me = threading.get_ident()
        if not self.reentrant and self.owner == me:
            raise RuntimeError(
                "this thread already holds the lock; taking it again would deadlock "
                "(pass reentrant=True to allow nesting)"
            )
        if not self.lock.acquire(True, -1 if timeout is None else timeout):
            return False
        try:
            if not self.reentrant:
                self.owner = me
        except BaseException:
            # Interrupted right after taking the lock: nobody would ever release it.
            self.lock.release()
            raise
        return True

    def release(self) -> None:
        """Give the lock back; called by the thread that acquired it."""
        if not self.reentrant:
            self.owner = None
        self.lock.release()


def drop_entry(entries: dict[Hashable, E], key: Hashable, entry: E) -> None:
    """Remove ``entry`` from the table, even if ``key`` changed its hash while held."""
    try:
        if entries.get(key) is entry:
            del entries[key]
            return
    except Exception:
        pass
    # The key no longer finds its own entry (a mutated key, an __eq__ that raises):
    # rebuild the table without it rather than leave a dead entry behind for ever.
    kept = {k: e for k, e in entries.items() if e is not entry}
    entries.clear()
    entries.update(kept)
