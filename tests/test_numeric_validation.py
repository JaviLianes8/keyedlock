"""Numeric validation checks the value used by the acquisition primitive."""

from __future__ import annotations

import asyncio
from fractions import Fraction

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


class MisleadingInt(int):
    def __lt__(self, other: object) -> bool:
        return False

    def __int__(self) -> int:
        return 4


class MisleadingFloat(float):
    def __lt__(self, other: object) -> bool:
        return False


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("value", [MisleadingInt(-1), MisleadingFloat(-1), Fraction(-1, 10**400)])
def test_negative_numeric_subclasses_are_rejected_before_acquisition(
    factory: type[KeyedLock | StripedLock | AsyncKeyedLock],
    group: bool,
    value: float,
) -> None:
    locks = factory()
    with pytest.raises(ValueError, match="non-negative"):
        if isinstance(locks, AsyncKeyedLock):

            async def run() -> None:
                manager = (
                    locks.lock_many([], timeout=value) if group else locks.lock(0, timeout=value)
                )
                async with manager:
                    pass

            asyncio.run(run())
        else:
            manager = locks.lock_many([], timeout=value) if group else locks.lock(0, timeout=value)
            with manager:
                pass


@pytest.mark.parametrize("value", [MisleadingInt(-1), MisleadingInt(0)])
def test_nonpositive_stripe_subclasses_are_rejected(value: int) -> None:
    with pytest.raises(ValueError, match="at least 1"):
        StripedLock(value)


def test_stripe_count_uses_the_underlying_integer() -> None:
    locks = StripedLock(MisleadingInt(2))
    assert locks.stripes == 2
    with locks.lock_many([0, 1], timeout=0):
        pass
