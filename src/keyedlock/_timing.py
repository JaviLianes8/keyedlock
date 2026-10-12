"""Timeout validation, shared deadlines and the key ordering used by ``lock_many``."""

from __future__ import annotations

import numbers
import threading
import time
from collections.abc import Hashable, Iterable
from itertools import pairwise
from typing import Any, TypeVar, cast

K = TypeVar("K", bound=Hashable)


def check_timeout(timeout: float | None) -> float | None:
    """Return the wait limit in seconds, or ``None`` to wait without limit.

    Anything above ``threading.TIMEOUT_MAX`` (infinity included) cannot be passed to a
    primitive, so it is treated as no limit rather than raising ``OverflowError``.
    """
    if timeout is None:
        return None
    if isinstance(timeout, bool) or not isinstance(timeout, numbers.Real):
        raise TypeError(f"timeout must be a real number or None, not {type(timeout).__name__}")
    # Compare before converting: a huge int would overflow float(), and NaN != NaN.
    if timeout != timeout or timeout < 0:
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
    message = "lock_many needs keys with a total order (all str, all int, ...; no NaN or sets)"
    try:
        result = sorted(cast("list[Any]", unique))
        # sorted() quietly keeps the input order for a partial order (sets, NaN), which
        # would let two callers take the same keys in opposite orders and deadlock.
        if not all(a < b for a, b in pairwise(result)):
            raise TypeError(message)
    except TypeError as error:
        raise TypeError(message) from error
    return cast("list[K]", result)


def timeout_error(what: str, timeout: float | None) -> TimeoutError:
    return TimeoutError(f"could not lock {what} within {timeout} seconds")
