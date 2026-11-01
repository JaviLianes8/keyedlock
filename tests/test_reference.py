"""Compare real standard-library output using schedules written for this project.

Sources fetched 2026-11-01: tests/upstream/MANIFEST.json, Python v3.14.0 docs.
The schedules below are authored cases, not copied upstream test vectors.
"""

from __future__ import annotations

import asyncio
import random
import threading
from collections.abc import Callable, Hashable, Iterator
from contextlib import AbstractAsyncContextManager, AbstractContextManager, contextmanager

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


async def queue_trace(
    context: Callable[[], AbstractAsyncContextManager[object]], seed: int
) -> list[int]:
    trace: list[int] = []
    rng = random.Random(seed)

    async def worker(index: int) -> None:
        async with context():
            trace.append(index)
            await asyncio.sleep(0)

    async with context():
        tasks = [asyncio.create_task(worker(i)) for i in range(200)]
        await asyncio.sleep(0)
        for index in rng.sample(range(1, 200), 80):
            tasks[index].cancel()
        await asyncio.sleep(0)
    tasks[0].cancel()  # cancellation between handoff and resumption
    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert all(item is None or isinstance(item, asyncio.CancelledError) for item in results)
    return trace


@pytest.mark.parametrize("seed", [7, 101, 20261101])
def test_async_fairness_and_cancellation_match_asyncio_lock(seed: int) -> None:
    async def main() -> None:
        oracle = asyncio.Lock()
        locks = AsyncKeyedLock()
        expected = await queue_trace(lambda: oracle, seed)
        actual = await queue_trace(lambda: locks.lock("shared"), seed)
        assert actual == expected
        assert len(actual) == 119
        assert locks.active_keys() == 0

    asyncio.run(main())


def thread_probe(context: Callable[[], AbstractContextManager[object]]) -> list[bool]:
    result: list[bool] = []

    def attempt() -> None:
        try:
            with context():
                result.append(True)
        except TimeoutError:
            result.append(False)

    with context():
        with context():
            worker = threading.Thread(target=attempt, daemon=True)
            worker.start()
            worker.join(5)
            assert not worker.is_alive()
        worker = threading.Thread(target=attempt, daemon=True)
        worker.start()
        worker.join(5)
        assert not worker.is_alive()
    attempt()
    return result


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
def test_reentrant_depth_matches_threading_rlock(factory: type[KeyedLock | StripedLock]) -> None:
    primitive = threading.RLock()

    @contextmanager
    def oracle() -> Iterator[None]:
        if not primitive.acquire(timeout=0):
            raise TimeoutError
        try:
            yield
        finally:
            primitive.release()

    locks = factory(reentrant=True)
    expected = thread_probe(oracle)
    assert expected == [False, False, True]
    assert thread_probe(lambda: locks.lock("shared", timeout=0)) == expected


@pytest.mark.parametrize("seed", [7, 101, 20261101])
def test_key_equality_matches_real_dict_output(seed: int) -> None:
    rng = random.Random(seed)
    pool: list[Hashable] = [1, 1.0, True, False, 0, 0.0, "a", "b", (1, 2), None]
    locks = KeyedLock(reentrant=True)
    for _ in range(1000):
        keys = rng.choices(pool, k=rng.randrange(30))
        from contextlib import ExitStack

        with ExitStack() as stack:
            for key in keys:
                stack.enter_context(locks.lock(key))
            assert locks.active_keys() == len(dict.fromkeys(keys))
        assert locks.active_keys() == 0
