"""Stored tuple and frozenset members obey exact structural boundaries."""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator
from contextlib import nullcontext

import pytest
from _acquisition import Factory, exercise

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


class HiddenTuple(tuple[Hashable, ...]):
    def __iter__(self) -> Iterator[Hashable]:
        return iter(())


class HiddenFrozenset(frozenset[Hashable]):
    def __iter__(self) -> Iterator[Hashable]:
        return iter(())


def wrap(kind: str, members: Iterable[Hashable]) -> Hashable:
    if kind == "tuple":
        return tuple(members)
    if kind == "frozenset":
        return frozenset(members)
    if kind == "hidden_tuple":
        return HiddenTuple(members)
    return HiddenFrozenset(members)


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize(
    "kind", ["tuple", "frozenset", "mixed", "hidden_tuple", "hidden_frozenset"]
)
@pytest.mark.parametrize("visits", [10000, 10001])
def test_visited_value_boundary(factory: Factory, group: bool, kind: str, visits: int) -> None:
    # A mixed root adds one tuple visit as well as each scalar member.
    key = (
        frozenset((tuple(range(visits - 2)),)) if kind == "mixed" else wrap(kind, range(visits - 1))
    )
    expected = (
        nullcontext()
        if visits == 10000
        else pytest.raises(ValueError, match=r"^key structure limit exceeded \(10000\)$")
    )
    locks = factory()
    with expected:
        exercise(locks, [key], group=group)
    exercise(locks, [0], group=group)


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize(
    "kind", ["tuple", "frozenset", "mixed", "hidden_tuple", "hidden_frozenset"]
)
@pytest.mark.parametrize("depth", [64, 65])
def test_stored_nesting_boundary(factory: Factory, group: bool, kind: str, depth: int) -> None:
    key: Hashable = 0
    for level in range(depth):
        container = ("tuple" if level % 2 else "frozenset") if kind == "mixed" else kind
        key = wrap(container, (key,))
    expected = (
        nullcontext()
        if depth == 64
        else pytest.raises(ValueError, match=r"^key nesting limit exceeded \(64\)$")
    )
    locks = factory()
    with expected:
        exercise(locks, [key], group=group)
    exercise(locks, [0], group=group)
