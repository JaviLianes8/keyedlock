"""Lock primitive shared by the keyed and striped locks."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol


class LockPrimitive(Protocol):
    """A blocking lock: anything with ``acquire`` and ``release``."""

    def acquire(self) -> bool: ...

    def release(self) -> None: ...


def lock_factory(reentrant: bool) -> Callable[[], LockPrimitive]:
    """Return a factory for reentrant (``RLock``) or plain (``Lock``) primitives."""
    if reentrant:
        return threading.RLock
    return threading.Lock
