"""Group deadlines, contended unlimited waits and body failures are observable."""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock, _primitive, _timing


def test_striped_group_spends_one_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [100.0]
    budgets: list[float | None] = []
    acquire = _primitive.Slot.acquire

    def delayed_acquire(slot: _primitive.Slot, timeout: float | None) -> bool:
        budgets.append(timeout)
        delay = 0.75 if len(budgets) == 1 else 0.5
        if timeout is not None and timeout < delay:
            now[0] += timeout
            return False
        now[0] += delay
        return acquire(slot, 0)

    locks = StripedLock(2)
    with monkeypatch.context() as patch:
        patch.setattr(_timing, "time", SimpleNamespace(monotonic=lambda: now[0]))
        patch.setattr(_primitive.Slot, "acquire", delayed_acquire)
        with pytest.raises(TimeoutError), locks.lock_many([0, 1], timeout=1):
            pass
    assert budgets == [1.0, 0.25]
    with locks.lock_many([0, 1], timeout=0):
        pass


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("huge", [float("inf"), threading.TIMEOUT_MAX * 2, 10**400])
def test_huge_timeout_waits_for_threaded_handoff(
    factory: type[KeyedLock | StripedLock],
    group: bool,
    huge: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locks = factory()
    attempting = threading.Event()
    outcomes: list[object] = []
    acquire = _primitive.Slot.acquire
    limits: list[float | None] = []
    waiter_id: list[int] = []

    def observed_acquire(slot: _primitive.Slot, timeout: float | None) -> bool:
        if waiter_id and threading.get_ident() == waiter_id[0]:
            limits.append(timeout)
            attempting.set()
        return acquire(slot, timeout)

    def wait() -> None:
        waiter_id.append(threading.get_ident())
        try:
            manager = (
                locks.lock_many([0, 1], timeout=huge) if group else locks.lock(0, timeout=huge)
            )
            with manager:
                outcomes.append("acquired")
        except Exception as error:
            outcomes.append(error)

    monkeypatch.setattr(_primitive.Slot, "acquire", observed_acquire)
    thread = threading.Thread(target=wait)
    try:
        with locks.lock(0):
            thread.start()
            assert attempting.wait(5)
            assert limits == [None]
    finally:
        thread.join(5)
    assert not thread.is_alive()
    assert outcomes == ["acquired"]
    if isinstance(locks, KeyedLock):
        assert locks.active_keys() == 0


@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("huge", [float("inf"), threading.TIMEOUT_MAX * 2, 10**400])
def test_huge_timeout_waits_for_async_handoff(group: bool, huge: float) -> None:
    async def run() -> None:
        locks = AsyncKeyedLock()

        async def wait() -> str:
            manager = (
                locks.lock_many([0, 1], timeout=huge) if group else locks.lock(0, timeout=huge)
            )
            async with manager:
                return "acquired"

        async with locks.lock(0):
            task = asyncio.create_task(wait())
            await asyncio.sleep(0)
            pending = not task.done()
        outcome = await asyncio.gather(task, return_exceptions=True)
        assert pending
        assert list(outcome) == ["acquired"]
        assert locks.active_keys() == 0

    asyncio.run(run())


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
def test_group_body_exception_identity_and_cleanup(factory: type[KeyedLock | StripedLock]) -> None:
    locks = factory()
    failure = LookupError("body failure")
    with pytest.raises(LookupError) as caught, locks.lock_many([0, 1]):
        raise failure
    assert caught.value is failure
    with locks.lock_many([0, 1], timeout=0):
        pass
    if isinstance(locks, KeyedLock):
        assert locks.active_keys() == 0


def test_async_group_body_exception_identity_and_cleanup() -> None:
    async def run() -> None:
        locks = AsyncKeyedLock()
        failure = LookupError("body failure")
        with pytest.raises(LookupError) as caught:
            async with locks.lock_many([0, 1]):
                raise failure
        assert caught.value is failure
        assert locks.active_keys() == 0
        async with locks.lock_many([0, 1], timeout=0):
            pass
        assert locks.active_keys() == 0

    asyncio.run(run())
