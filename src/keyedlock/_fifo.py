"""A first come, first served asyncio lock whose waits can carry a timeout."""

from __future__ import annotations

import asyncio
from collections import deque


def _expire(future: asyncio.Future[bool]) -> None:
    if not future.done():
        future.set_result(False)


class FifoLock:
    """An asyncio mutex that hands ownership straight to the oldest waiter.

    Timed and untimed waiters share one queue, so a timeout never costs a waiter its
    place, and no helper task is involved. Release passes the lock on without ever
    unlocking it in between, so a newcomer cannot slip past the queue. Invariant: when
    the lock is free, nobody is queued.
    """

    __slots__ = ("_locked", "_waiters")

    def __init__(self) -> None:
        self._locked = False
        self._waiters: deque[asyncio.Future[bool]] = deque()

    def locked(self) -> bool:
        return self._locked

    async def acquire(self, timeout: float | None) -> bool:
        """Take the lock, waiting at most ``timeout`` seconds; ``False`` if it ran out."""
        if not self._locked:
            self._locked = True
            return True
        if timeout == 0:
            return False
        loop = asyncio.get_running_loop()
        future: asyncio.Future[bool] = loop.create_future()
        self._waiters.append(future)
        timer = None if timeout is None else loop.call_later(timeout, _expire, future)
        try:
            return await future
        except BaseException:
            # Cancelled after the lock was already handed over: pass it on.
            if future.done() and not future.cancelled() and future.result():
                self.release()
            raise
        finally:
            if timer is not None:
                timer.cancel()
            if future in self._waiters:
                self._waiters.remove(future)

    def release(self) -> None:
        """Hand the lock to the oldest live waiter, or free it when there is none."""
        if not self._locked:
            raise RuntimeError("release of an unlocked lock")
        while self._waiters:
            future = self._waiters.popleft()
            if not future.done():
                future.set_result(True)
                return
        self._locked = False
