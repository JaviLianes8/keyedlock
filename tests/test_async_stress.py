"""Hundreds of tasks with timeouts, failures and cancellation: exclusion holds, nothing leaks."""

from __future__ import annotations

import asyncio
import random

from keyedlock import AsyncKeyedLock
from keyedlock._async import _abandon

TASKS = 300
KEYS = 5


def test_invariants_hold_under_timeouts_and_cancellation() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        rng = random.Random(7)
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
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.sleep(0)
        assert overlaps == 0
        assert totals == entered
        assert sum(entered) > TASKS // 4
        assert lock.active_keys() == 0
        for key in range(KEYS):
            async with lock.lock(key, timeout=0):
                pass

    asyncio.run(main())


def test_an_abandoned_attempt_that_won_the_lock_releases_it() -> None:
    async def main() -> None:
        lock = asyncio.Lock()
        attempt = asyncio.ensure_future(lock.acquire())
        await asyncio.sleep(0)
        assert attempt.done() and lock.locked()
        _abandon(attempt, lock)
        await asyncio.sleep(0)
        assert not lock.locked()

    asyncio.run(main())


def test_an_abandoned_attempt_still_waiting_does_not_take_the_lock() -> None:
    async def main() -> None:
        lock = asyncio.Lock()
        await lock.acquire()
        attempt = asyncio.ensure_future(lock.acquire())
        await asyncio.sleep(0)
        _abandon(attempt, lock)
        lock.release()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert attempt.cancelled()
        assert not lock.locked()

    asyncio.run(main())
