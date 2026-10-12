"""Taking a key twice on one thread fails fast unless the lock is reentrant."""

from __future__ import annotations

import pytest

from keyedlock import KeyedLock, StripedLock


def test_keyed_reentry_raises_instead_of_deadlocking() -> None:
    lock = KeyedLock()
    with lock.lock("x"):
        with pytest.raises(RuntimeError, match="already holds"), lock.lock("x", timeout=0.5):
            pass
        assert lock.active_keys() == 1
    assert lock.active_keys() == 0
    with lock.lock("x", timeout=0):
        pass


def test_keyed_reentrant_mode_allows_nesting() -> None:
    lock = KeyedLock(reentrant=True)
    with lock.lock("x"), lock.lock("x", timeout=0):
        assert lock.active_keys() == 1
    assert lock.active_keys() == 0


def test_different_keys_nest_freely() -> None:
    lock = KeyedLock()
    with lock.lock("a"), lock.lock("b", timeout=0.5):
        assert lock.active_keys() == 2


def test_striped_nesting_on_a_shared_stripe_raises() -> None:
    # One stripe means every key shares it: nesting two different keys used to deadlock.
    lock = StripedLock(stripes=1)
    with (
        lock.lock("a"),
        pytest.raises(RuntimeError, match="already holds"),
        lock.lock("b", timeout=0.5),
    ):
        pass
    with lock.lock("b", timeout=0):
        pass


def test_striped_reentrant_mode_allows_nesting_on_a_shared_stripe() -> None:
    lock = StripedLock(stripes=1, reentrant=True)
    with lock.lock("a"), lock.lock("b", timeout=0):
        pass


def test_reentry_is_per_thread() -> None:
    import threading

    lock = KeyedLock()
    outcome: list[str] = []
    with lock.lock("x"):

        def other() -> None:
            try:
                with lock.lock("x", timeout=0.05):
                    outcome.append("entered")
            except TimeoutError:
                outcome.append("timeout")

        thread = threading.Thread(target=other)
        thread.start()
        thread.join(5)
    # Another thread waits (and times out) rather than being told it re-entered.
    assert outcome == ["timeout"]
