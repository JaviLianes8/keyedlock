"""Lock by key: same key serializes, different keys run in parallel."""

from __future__ import annotations

from ._keyed import KeyedLock
from ._striped import StripedLock

__version__ = "0.1.0"

__all__ = ["KeyedLock", "StripedLock"]
