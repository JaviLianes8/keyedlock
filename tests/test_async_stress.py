"""Hundreds of tasks with timeouts, failures and cancellation: exclusion holds, nothing leaks."""

from __future__ import annotations

import asyncio
import random

import pytest

from keyedlock import AsyncKeyedLock

TASKS = 300
KEYS = 5


@pytest.mark.parametrize("seed", [7, 101, 20261101])
def test_invariants_hold_under_timeouts_and_cancellation(seed: int) -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        rng = random.Random(seed)
        inside = [0] * KEYS
        totals = [0] * KEYS
        entered = [0] * KEYS
        overlaps = 0

        async def worker() -> None:
            nonlocal overlaps
            keys = rng.sample(range(KEYS), rng.choice((1, 1, 2)))
            timeout = rng.choice((None, 0, 0.001, 0.005))
            manager = (
                lock.lock(keys[0], timeout=timeout)
                if len(keys) == 1
                else lock.lock_many(keys, timeout=timeout)
            )
            try:
                async with manager:
                    counted: list[int] = []
                    try:
                        for key in keys:
                            inside[key] += 1
                            counted.append(key)
                            overlaps += inside[key] != 1
                            total = totals[key]
                            await asyncio.sleep(0)
                            totals[key] = total + 1
                            entered[key] += 1
                        if rng.random() < 0.1:
                            raise ValueError("work failed")
                        await asyncio.sleep(0)
                    finally:
                        for key in counted:
                            inside[key] -= 1
            except (TimeoutError, ValueError):
                pass

        tasks = [asyncio.create_task(worker()) for _ in range(TASKS)]
        for _ in range(TASKS // 3):
            await asyncio.sleep(0)
            rng.choice(tasks).cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert all(
            result is None or isinstance(result, asyncio.CancelledError) for result in results
        )
        await asyncio.sleep(0)
        assert overlaps == 0
        assert totals == entered
        assert sum(entered) > TASKS // 4
        assert lock.active_keys() == 0
        for key in range(KEYS):
            async with lock.lock(key, timeout=0):
                pass

    asyncio.run(main())


def test_a_timed_waiter_keeps_its_place_ahead_of_a_later_untimed_one() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        order: list[str] = []

        async def go(name: str, timeout: float | None) -> None:
            async with lock.lock("k", timeout=timeout):
                order.append(name)

        async with lock.lock("k"):
            first = asyncio.create_task(go("timed-first", 5))
            second = asyncio.create_task(go("untimed-second", None))
            await asyncio.sleep(0)
        await asyncio.gather(first, second)
        assert order == ["timed-first", "untimed-second"]
        assert lock.active_keys() == 0

    asyncio.run(main())
