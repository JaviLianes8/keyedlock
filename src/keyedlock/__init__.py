"""Lock by key: same key serializes, different keys run in parallel."""

from __future__ import annotations

from ._async import AsyncKeyedLock
from ._keyed import KeyedLock
from ._striped import StripedLock

del annotations

__version__ = "1.0.0"

__all__ = ["AsyncKeyedLock", "KeyedLock", "StripedLock"]

for _class in (AsyncKeyedLock, KeyedLock, StripedLock):
    _class.__module__ = __name__
del _class
