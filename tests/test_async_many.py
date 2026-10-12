"""AsyncKeyedLock.lock_many: sorted, deduplicated, all or nothing."""

from __future__ import annotations

import asyncio

import pytest

from keyedlock import AsyncKeyedLock


def test_lock_many_orders_keys_and_is_all_or_nothing() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()

        async def take(keys: list[int]) -> None:
            for _ in range(200):
                async with lock.lock_many(keys, timeout=10):
                    await asyncio.sleep(0)

        await asyncio.wait_for(asyncio.gather(take([1, 2]), take([2, 1])), 20)
        async with lock.lock("c"):
            with pytest.raises(TimeoutError):
                await asyncio.create_task(_enter_many(lock, ["a", "b", "c"], 0.01))
            assert lock.active_keys() == 1
        with pytest.raises(TypeError, match="single str"):
            async with lock.lock_many("ab"):
                pass
        assert lock.active_keys() == 0

    asyncio.run(main())


async def _enter_many(lock: AsyncKeyedLock, keys: list[str], timeout: float | None) -> None:
    async with lock.lock_many(keys, timeout=timeout):
        pass


def test_later_keys_get_only_what_is_left_of_the_budget() -> None:
    # "a" frees at 0.4 s and "b" at 0.8 s; one shared 0.6 s budget gives up on "b".
    async def main() -> None:
        lock = AsyncKeyedLock()

        async def hold(key: str, seconds: float) -> None:
            async with lock.lock(key):
                await asyncio.sleep(seconds)

        holders = [asyncio.create_task(hold("a", 0.4)), asyncio.create_task(hold("b", 0.8))]
        await asyncio.sleep(0)
        with pytest.raises(TimeoutError, match="'b'"):
            async with lock.lock_many(["a", "b"], timeout=0.6):
                pass
        await asyncio.gather(*holders)
        assert lock.active_keys() == 0

    asyncio.run(main())
