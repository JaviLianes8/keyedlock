"""Group operations, async validation and cleanup through public entry points."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


def broken_keys() -> Iterator[int]:
    yield 1
    raise LookupError("input iteration failed")


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
def test_iterables_are_consumed_before_taking_any_lock(
    factory: type[KeyedLock | StripedLock],
) -> None:
    locks = factory()
    with pytest.raises(LookupError), locks.lock_many(broken_keys()):
        pass
    with locks.lock(1, timeout=0):
        pass
    if isinstance(locks, KeyedLock):
        assert locks.active_keys() == 0


def test_striped_groups_allow_mixed_types() -> None:
    locks = StripedLock(1)
    with (
        locks.lock_many(["a", 1, None, (1, 2)]),
        pytest.raises(RuntimeError),
        locks.lock("any"),
    ):
        pass
    with locks.lock("any", timeout=0):
        pass


def test_async_group_cleanup_and_yield_value() -> None:
    async def main() -> None:
        locks = AsyncKeyedLock()
        async with locks.lock_many([]) as held:
            assert held is None
            assert locks.active_keys() == 0
        async with locks.lock_many(["b", "a", "a"]) as held:
            assert held is None
            assert locks.active_keys() == 2
            for key in "ab":
                with pytest.raises(RuntimeError):
                    async with locks.lock(key):
                        pass
        with pytest.raises(LookupError):
            async with locks.lock_many(broken_keys()):
                pass
        assert locks.active_keys() == 0

    asyncio.run(main())


@pytest.mark.parametrize("bad", [True, "1", 1j, object()])
def test_async_checks_timeout_even_for_an_empty_batch(bad: object) -> None:
    async def main() -> None:
        locks = AsyncKeyedLock()
        for manager in (locks.lock("k", timeout=bad), locks.lock_many([], timeout=bad)):  # type: ignore[arg-type]
            with pytest.raises(TypeError):
                async with manager:
                    pass
        assert locks.active_keys() == 0

    asyncio.run(main())


def test_async_cancelled_partial_group_releases_acquired_keys() -> None:
    async def main() -> None:
        locks = AsyncKeyedLock()
        entered = asyncio.Event()

        async def group() -> None:
            entered.set()
            async with locks.lock_many(["a", "b"], timeout=10):
                pytest.fail("entered a group with a blocked key")

        async with locks.lock("b"):
            task = asyncio.create_task(group())
            await entered.wait()
            assert locks.active_keys() == 2
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert locks.active_keys() == 1
            async with locks.lock("a", timeout=0):
                pass
        assert locks.active_keys() == 0

    asyncio.run(main())


def test_async_cancelled_holder_releases_the_key() -> None:
    async def main() -> None:
        locks = AsyncKeyedLock()
        entered = asyncio.Event()
        never = asyncio.Event()

        async def holder() -> None:
            async with locks.lock("a"):
                entered.set()
                await never.wait()

        task = asyncio.create_task(holder())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert locks.active_keys() == 0
        async with locks.lock("a", timeout=0) as held:
            assert held is None

    asyncio.run(main())
