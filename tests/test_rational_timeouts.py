"""Authored rational timeout cases pin component validation and immediate acquisition."""

from __future__ import annotations

import asyncio
import threading
from fractions import Fraction
from typing import cast

import pytest
from _acquisition import Factory, exercise
from _timeout_values import IntOnlyComponent, rational_timeout

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock

ZERO_TIMEOUTS = [
    pytest.param(cast(float, Fraction(0, 1)), id="fraction-zero"),
    pytest.param(rational_timeout(0, -2), id="zero-negative-denominator"),
]


class UntouchedKey:
    def __hash__(self) -> int:
        pytest.fail("invalid timeout reached key hashing")


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("member", ["numerator", "denominator"])
@pytest.mark.parametrize(
    "component",
    [pytest.param(2.5, id="float"), pytest.param("2", id="string"), IntOnlyComponent()],
)
def test_rational_components_require_index_protocol(
    factory: Factory, group: bool, member: str, component: object
) -> None:
    value = (
        rational_timeout(component, 2) if member == "numerator" else rational_timeout(1, component)
    )
    locks = factory()
    with pytest.raises(TypeError) as caught:
        exercise(locks, [UntouchedKey()], group=group, timeout=value)
    assert str(caught.value) == "timeout must be a real number or None (not bool)"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    exercise(locks, [0, 1], group=group)


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("numerator", [-1, 0, 1])
def test_zero_denominator_raises_valueerror_before_acquisition(
    factory: Factory, group: bool, numerator: int
) -> None:
    locks = factory()
    with pytest.raises(ValueError) as caught:
        exercise(locks, [UntouchedKey()], group=group, timeout=rational_timeout(numerator, 0))
    assert str(caught.value) == "timeout must be None or a non-negative number"
    exercise(locks, [0, 1], group=group)


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
def test_negative_denominator_underflow_raises_before_acquisition(
    factory: Factory, group: bool
) -> None:
    locks = factory()
    with pytest.raises(ValueError) as caught:
        exercise(locks, [UntouchedKey()], group=group, timeout=rational_timeout(1, -(10**400)))
    assert str(caught.value) == "timeout must be None or a non-negative number"
    exercise(locks, [0, 1], group=group)


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("value", ZERO_TIMEOUTS)
def test_zero_fraction_succeeds_on_free_keys(factory: Factory, group: bool, value: float) -> None:
    locks = factory()
    exercise(locks, [0, 1], group=group, timeout=value)
    exercise(locks, [0, 1], group=group)


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("value", ZERO_TIMEOUTS)
def test_zero_fraction_fails_without_waiting_on_held_threaded_keys(
    factory: type[KeyedLock | StripedLock], group: bool, value: float
) -> None:
    locks = factory()
    outcomes: list[Exception] = []

    def attempt() -> None:
        manager = locks.lock_many([0, 1], timeout=value) if group else locks.lock(1, timeout=value)
        try:
            with manager:
                outcomes.append(AssertionError("entered a held lock"))
        except Exception as error:
            outcomes.append(error)

    thread = threading.Thread(target=attempt, daemon=True)
    try:
        with locks.lock(1):
            thread.start()
            thread.join(5)
            assert not thread.is_alive(), "zero timeout waited for the holder to release"
            assert len(outcomes) == 1 and isinstance(outcomes[0], TimeoutError)
            if isinstance(locks, KeyedLock):
                assert locks.active_keys() == 1
            with locks.lock(0, timeout=0):
                pass
    finally:
        thread.join(5)
    exercise(locks, [0, 1], group=group)


@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("value", ZERO_TIMEOUTS)
def test_zero_fraction_fails_without_waiting_on_held_async_keys(group: bool, value: float) -> None:
    async def run() -> None:
        locks = AsyncKeyedLock()

        async def attempt() -> None:
            manager = (
                locks.lock_many([0, 1], timeout=value) if group else locks.lock(1, timeout=value)
            )
            async with manager:
                pytest.fail("entered a held lock")

        async with locks.lock(1):
            task = asyncio.create_task(attempt())
            try:
                await asyncio.sleep(0)
                assert task.done(), "zero timeout suspended while waiting for the holder"
                with pytest.raises(TimeoutError):
                    await task
                assert locks.active_keys() == 1
                async with locks.lock(0, timeout=0):
                    pass
            finally:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
        assert locks.active_keys() == 0
        async with locks.lock_many([0, 1], timeout=0):
            pass
        assert locks.active_keys() == 0

    asyncio.run(run())
