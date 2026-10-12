"""FifoLock: strict hand-off order, timeouts and cancellation that never strand the lock."""

from __future__ import annotations

import asyncio

import pytest

from keyedlock._fifo import FifoLock, _expire


def test_a_free_lock_is_taken_without_suspending() -> None:
    async def main() -> None:
        lock = FifoLock()
        ran: list[int] = []
        asyncio.get_running_loop().call_soon(ran.append, 1)
        assert await lock.acquire(0)
        assert ran == [] and lock.locked()

    asyncio.run(main())


def test_release_of_a_free_lock_raises() -> None:
    with pytest.raises(RuntimeError):
        FifoLock().release()


def test_timed_and_untimed_waiters_share_one_queue() -> None:
    async def main() -> None:
        lock = FifoLock()
        order: list[str] = []

        async def take(name: str, timeout: float | None) -> None:
            assert await lock.acquire(timeout)
            order.append(name)
            lock.release()

        await lock.acquire(None)
        tasks = [
            asyncio.create_task(take("timed-first", 5)),
            asyncio.create_task(take("untimed-second", None)),
            asyncio.create_task(take("timed-third", 5)),
        ]
        await asyncio.sleep(0)
        lock.release()
        await asyncio.gather(*tasks)
        assert order == ["timed-first", "untimed-second", "timed-third"]
        assert not lock.locked()

    asyncio.run(main())


def test_a_newcomer_cannot_overtake_a_waiter_being_handed_the_lock() -> None:
    async def main() -> None:
        lock = FifoLock()
        await lock.acquire(None)
        waiter = asyncio.create_task(lock.acquire(None))
        await asyncio.sleep(0)
        lock.release()  # handed to the waiter, which has not run yet
        assert lock.locked()
        assert not await lock.acquire(0)
        assert await waiter

    asyncio.run(main())


def test_cancelled_after_the_hand_off_passes_the_lock_on() -> None:
    async def main() -> None:
        lock = FifoLock()
        await lock.acquire(None)
        first = asyncio.create_task(lock.acquire(None))
        second = asyncio.create_task(lock.acquire(None))
        await asyncio.sleep(0)
        lock.release()  # hands to first...
        first.cancel()  # ...which is cancelled before it resumes
        with pytest.raises(asyncio.CancelledError):
            await first
        assert await asyncio.wait_for(second, 5)
        lock.release()
        assert not lock.locked()

    asyncio.run(main())


def test_an_expired_waiter_leaves_the_queue_and_the_lock_free() -> None:
    async def main() -> None:
        lock = FifoLock()
        await lock.acquire(None)
        assert not await lock.acquire(0.01)
        lock.release()
        assert not lock.locked()
        assert await lock.acquire(0)

    asyncio.run(main())


def test_a_waiter_cancelled_in_the_queue_does_not_take_the_lock() -> None:
    async def main() -> None:
        lock = FifoLock()
        await lock.acquire(None)
        waiter = asyncio.create_task(lock.acquire(10))
        await asyncio.sleep(0)
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        lock.release()
        assert not lock.locked()

    asyncio.run(main())


def test_zero_timeout_on_a_held_lock_fails_without_suspending() -> None:
    async def main() -> None:
        lock = FifoLock()
        await lock.acquire(None)
        ran: list[int] = []
        asyncio.get_running_loop().call_soon(ran.append, 1)
        assert not await lock.acquire(0)
        assert ran == []

    asyncio.run(main())


def test_a_finished_wait_leaves_no_queue_entry_or_timer_behind() -> None:
    async def main() -> None:
        lock = FifoLock()
        loop = asyncio.get_running_loop()
        await lock.acquire(None)
        assert not await lock.acquire(0.01)  # expired
        assert not lock._waiters
        waiter = asyncio.create_task(lock.acquire(60))
        await asyncio.sleep(0)
        lock.release()
        assert await waiter  # handed over well before its 60 s timer
        assert not lock._waiters
        timers = [h for h in loop._scheduled if not h.cancelled()]  # type: ignore[attr-defined]
        assert timers == []

    asyncio.run(main())


def test_expiry_after_the_hand_off_is_a_no_op() -> None:
    async def main() -> None:
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        future.set_result(True)
        _expire(future)
        assert future.result() is True

    asyncio.run(main())
