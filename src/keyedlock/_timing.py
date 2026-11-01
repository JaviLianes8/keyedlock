"""Timeout validation, shared deadlines and the key ordering used by ``lock_many``."""

from __future__ import annotations

import numbers
import operator
import threading
import time
from collections.abc import Hashable, Iterable
from itertools import pairwise
from typing import Any, TypeVar, cast

from ._keys import iter_keys
from ._table import KeyTable

K = TypeVar("K", bound=Hashable)


def check_timeout(timeout: float | None) -> float | None:
    """Return the wait limit in seconds, or ``None`` to wait without limit.

    Anything above ``threading.TIMEOUT_MAX`` (infinity included) cannot be passed to a
    primitive, so it is treated as no limit rather than raising ``OverflowError``.
    """
    if timeout is None:
        return None
    if isinstance(timeout, bool) or not isinstance(timeout, numbers.Real):
        raise TypeError("timeout must be a real number or None (not bool)")
    try:
        # Integer subclasses must not override the sign or magnitude used below.
        if isinstance(timeout, int):
            integer = int.__index__(timeout)
            if integer < 0:
                raise ValueError("timeout must be None or a non-negative number")
            if integer > threading.TIMEOUT_MAX:
                return None
            value = float(integer)
        elif isinstance(timeout, numbers.Rational):
            numerator = operator.index(timeout.numerator)
            denominator = operator.index(timeout.denominator)
            if denominator == 0 or (numerator != 0 and (numerator < 0) != (denominator < 0)):
                raise ValueError("timeout must be None or a non-negative number")
            try:
                value = numerator / denominator
            except OverflowError:
                return None
        else:
            value = float(timeout)
    except TypeError as error:
        # A Python conversion method adds a frame; preserve its explicit failure.
        if error.__traceback__ is not None and error.__traceback__.tb_next is not None:
            raise
        raise TypeError("timeout must be a real number or None (not bool)") from None
    if value != value or value < 0:
        raise ValueError("timeout must be None or a non-negative number")
    if value > threading.TIMEOUT_MAX:
        return None
    return value


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
    table: KeyTable[K, K] = KeyTable()
    for key in iter_keys(keys):
        table.intern(key, lambda item: item)
    unique = list(table.values())
    message = "lock_many needs keys with a total order (all str, all int, ...; no NaN or sets)"
    try:
        result = sorted(cast("list[Any]", unique))
        # sorted() quietly keeps the input order for a partial order (sets, NaN), which
        # would let two callers take the same keys in opposite orders and deadlock.
        if not all(a < b for a, b in pairwise(result)):
            raise TypeError(message)
    except TypeError:
        raise TypeError(message) from None
    return cast("list[K]", result)


def timeout_error(what: str, timeout: float | None) -> TimeoutError:
    return TimeoutError(f"could not lock {what} within {timeout} seconds")
