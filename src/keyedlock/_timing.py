"""Timeout validation, shared deadlines and the key ordering used by ``lock_many``."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Hashable, Iterable
from typing import Any, TypeVar, cast

K = TypeVar("K", bound=Hashable)


def check_timeout(timeout: float | None) -> float | None:
    """Return the wait limit in seconds, or ``None`` to wait without limit.

    Anything above ``threading.TIMEOUT_MAX`` (infinity included) cannot be passed to a
    primitive, so it is treated as no limit rather than raising ``OverflowError``.
    """
    if timeout is None:
        return None
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise TypeError(f"timeout must be a number or None, not {type(timeout).__name__}")
    if math.isnan(timeout) or timeout < 0:
        raise ValueError("timeout must be None or a non-negative number")
    if timeout > threading.TIMEOUT_MAX:
        return None
    return float(timeout)


class Deadline:
    """One timeout budget spent across several acquisitions."""

    def __init__(self, timeout: float | None) -> None:
        self._end = None if timeout is None else time.monotonic() + timeout

    def remaining(self) -> float | None:
        if self._end is None:
            return None
        return max(0.0, self._end - time.monotonic())


def ordered(keys: Iterable[K]) -> list[K]:
    """Deduplicate ``keys`` and sort them, so every caller takes them in the same order."""
    if isinstance(keys, (str, bytes)):
        raise TypeError("keys must be a collection of keys, not a single str or bytes")
    unique = list(dict.fromkeys(keys))
    try:
        return cast("list[K]", sorted(cast("list[Any]", unique)))
    except TypeError as error:
        raise TypeError("lock_many needs keys that can be sorted against each other") from error


def timeout_error(what: str, timeout: float | None) -> TimeoutError:
    return TimeoutError(f"could not lock {what} within {timeout} seconds")
