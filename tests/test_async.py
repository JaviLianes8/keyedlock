"""AsyncKeyedLock: exclusion, fairness, timeouts and cancellation without residue."""

from __future__ import annotations

import asyncio

import pytest

from keyedlock import AsyncKeyedLock


def test_same_key_serializes_and_cleans_up() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        inside = {"n": 0, "peak": 0}

        async def worker() -> None:
            async with lock.lock("k"):
                inside["n"] += 1
                inside["peak"] = max(inside["peak"], inside["n"])
                await asyncio.sleep(0)
                inside["n"] -= 1

        await asyncio.gather(*(worker() for _ in range(20)))
        assert inside["peak"] == 1
        assert lock.active_keys() == 0

    asyncio.run(main())


def test_different_keys_run_concurrently() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        both = asyncio.Event()
        count = {"in": 0}

        async def worker(key: str) -> None:
            async with lock.lock(key):
                count["in"] += 1
                if count["in"] == 2:
                    both.set()
                await asyncio.wait_for(both.wait(), 5)

        await asyncio.gather(worker("a"), worker("b"))

    asyncio.run(main())


def test_waiters_are_served_first_come_first_served() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        order: list[int] = []

        async def worker(n: int) -> None:
            async with lock.lock("k"):
                order.append(n)
                await asyncio.sleep(0)

        async with lock.lock("k"):
            tasks = []
            for n in range(10):
                tasks.append(asyncio.create_task(worker(n)))
                await asyncio.sleep(0)  # let each one queue before the next
        await asyncio.gather(*tasks)
        assert order == list(range(10))

    asyncio.run(main())


def test_timeouts_raise_and_leave_nothing_behind() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        async with lock.lock("k"):
            for timeout in (0, 0.01):
                with pytest.raises(TimeoutError, match="'k'"):
                    await asyncio.create_task(_enter(lock, "k", timeout))
            assert lock.active_keys() == 1
        await asyncio.sleep(0)
        assert lock.active_keys() == 0
        async with lock.lock("k", timeout=0):
            assert lock.active_keys() == 1

    asyncio.run(main())


def test_zero_timeout_on_a_free_key_succeeds() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        async with lock.lock("k", timeout=0):
            assert lock.active_keys() == 1

    asyncio.run(main())


def test_a_timeout_is_met_when_the_holder_leaves_in_time() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        entered = asyncio.Event()

        async def holder() -> None:
            async with lock.lock("k"):
                entered.set()
                await asyncio.sleep(0.02)

        task = asyncio.create_task(holder())
        await entered.wait()
        async with lock.lock("k", timeout=5):
            pass
        await task
        assert lock.active_keys() == 0

    asyncio.run(main())


def test_cancelling_a_waiter_leaves_nothing_behind() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        for timeout in (None, 10):
            async with lock.lock("k"):
                waiter = asyncio.create_task(_enter(lock, "k", timeout))
                await asyncio.sleep(0.01)
                waiter.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await waiter
            await asyncio.sleep(0)
            assert lock.active_keys() == 0
            async with lock.lock("k", timeout=0):
                pass

    asyncio.run(main())


async def _enter(lock: AsyncKeyedLock, key: str, timeout: float | None) -> None:
    async with lock.lock(key, timeout=timeout):
        pass


def test_reentry_by_the_same_task_raises() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        async with lock.lock("k"):
            with pytest.raises(RuntimeError, match="already holds"):
                async with lock.lock("k", timeout=0.5):
                    pass
            assert lock.active_keys() == 1
        assert lock.active_keys() == 0

    asyncio.run(main())


def test_an_exception_in_the_body_releases_the_key() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        with pytest.raises(KeyError):
            async with lock.lock("k"):
                raise KeyError("boom")
        assert lock.active_keys() == 0

    asyncio.run(main())


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
