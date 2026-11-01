"""Bound built-in key structure and normalize built-in protocol failures."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator
from typing import TypeVar

K = TypeVar("K", bound=Hashable)


def checked_hash(key: Hashable) -> int:
    # Inspect before hashing: CPython's recursive tuple hash can exhaust the C stack.
    stack: list[Iterator[object]] = [iter((key,))]
    visited = 0
    while stack:
        try:
            value = next(stack[-1])
        except StopIteration:
            stack.pop()
            continue
        visited += 1
        if visited > 10000:
            raise ValueError("key structure limit exceeded (10000)")
        if isinstance(value, (tuple, frozenset)):
            if len(stack) > 64:
                raise ValueError("key nesting limit exceeded (64)")
            # Built-in hashing sees the stored members, not an overridden __iter__.
            members = (
                tuple.__iter__(value) if isinstance(value, tuple) else frozenset.__iter__(value)
            )
            stack.append(members)
    try:
        return hash(key)
    except (TypeError, ValueError) as error:
        # A Python key method adds a traceback frame; preserve its explicit failure.
        if error.__traceback__ is not None and error.__traceback__.tb_next is not None:
            raise
        raise TypeError("key must be hashable") from None


def iter_keys(keys: Iterable[K]) -> Iterator[K]:
    if isinstance(keys, (str, bytes)):
        raise TypeError("keys must be a collection of keys, not a single str or bytes")
    try:
        return iter(keys)
    except TypeError as error:
        if error.__traceback__ is not None and error.__traceback__.tb_next is not None:
            raise
        raise TypeError("keys must be an iterable of keys") from None
