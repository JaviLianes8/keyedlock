"""lock_many takes several keys in one global order and is all or nothing."""

from __future__ import annotations

import threading
from collections.abc import Callable

import pytest
from _helpers import run_threads

from keyedlock import KeyedLock, StripedLock


def _opposite_orders(take: Callable[[list[int]], object], rounds: int = 300) -> None:
    # Two threads repeatedly lock the same pair in opposite orders: with naive nesting
    # this deadlocks within a few rounds; sorted acquisition never does.
    start = threading.Barrier(2)

    def worker(keys: list[int]) -> Callable[[], None]:
        def run() -> None:
            start.wait()
            for _ in range(rounds):
                take(keys)

        return run

    run_threads([worker([1, 2]), worker([2, 1])], timeout=20)


def test_keyed_lock_many_never_deadlocks_on_opposite_orders() -> None:
    lock = KeyedLock()

    def take(keys: list[int]) -> None:
        with lock.lock_many(keys, timeout=10):
            pass

    _opposite_orders(take)
    assert lock.active_keys() == 0


def test_striped_lock_many_never_deadlocks_on_opposite_orders() -> None:
    lock = StripedLock(stripes=8)

    def take(keys: list[int]) -> None:
        with lock.lock_many(keys, timeout=10):
            pass

    _opposite_orders(take)


def test_keyed_lock_many_holds_every_key() -> None:
    lock = KeyedLock()
    with lock.lock_many(["b", "a", "c"]):
        assert lock.active_keys() == 3
        for key in "abc":
            with pytest.raises(RuntimeError):  # held by this thread
                lock.lock(key, timeout=0).__enter__()
    assert lock.active_keys() == 0


def test_duplicates_are_taken_once() -> None:
    lock = KeyedLock()
    with lock.lock_many(["a", "a", "b"]):
        assert lock.active_keys() == 2
    striped = StripedLock(stripes=1)
    with striped.lock_many(["a", "b", "c"]):  # all on one stripe: taken once
        pass


def test_an_empty_collection_locks_nothing() -> None:
    lock = KeyedLock()
    with lock.lock_many([]):
        assert lock.active_keys() == 0


def test_a_failure_part_way_releases_what_was_taken() -> None:
    lock = KeyedLock()
    release = threading.Event()
    holding = threading.Event()

    def hold_c() -> None:
        with lock.lock("c"):
            holding.set()
            release.wait(10)

    thread = threading.Thread(target=hold_c)
    thread.start()
    assert holding.wait(5)
    with pytest.raises(TimeoutError), lock.lock_many(["a", "b", "c"], timeout=0.05):
        pass
    assert lock.active_keys() == 1  # only the other thread's "c"
    with lock.lock_many(["a", "b"], timeout=0):
        pass
    release.set()
    thread.join(5)
    assert lock.active_keys() == 0


def test_the_timeout_covers_the_whole_acquisition() -> None:
    lock = StripedLock(stripes=8)
    release = threading.Event()
    holding = threading.Event()

    def hold() -> None:
        with lock.lock(3):
            holding.set()
            release.wait(10)

    thread = threading.Thread(target=hold)
    thread.start()
    assert holding.wait(5)
    with pytest.raises(TimeoutError, match="stripe 3"), lock.lock_many([1, 2, 3], timeout=0.05):
        pass
    with lock.lock_many([1, 2], timeout=0):
        pass
    release.set()
    thread.join(5)


@pytest.mark.parametrize("keys", ["abc", b"abc"])
def test_a_bare_string_is_rejected(keys: str | bytes) -> None:
    with pytest.raises(TypeError, match="single str"), KeyedLock().lock_many(keys):
        pass
    with pytest.raises(TypeError, match="single str"), StripedLock().lock_many(keys):
        pass


def test_keys_that_cannot_be_sorted_are_rejected_before_locking() -> None:
    lock = KeyedLock()
    with pytest.raises(TypeError, match="sorted"), lock.lock_many(["a", 1]):
        pass
    assert lock.active_keys() == 0


def test_later_keys_get_only_what_is_left_of_the_budget() -> None:
    # "a" frees at 0.4 s and "b" at 0.8 s. With one shared 0.6 s budget the wait for "b"
    # gives up at 0.6 s; a fresh 0.6 s per key would wrongly succeed at 0.8 s.
    lock = KeyedLock()
    ready = threading.Barrier(3)

    def hold(key: str, seconds: float) -> Callable[[], None]:
        def run() -> None:
            with lock.lock(key):
                ready.wait()
                threading.Event().wait(seconds)

        return run

    holders = [threading.Thread(target=hold("a", 0.4)), threading.Thread(target=hold("b", 0.8))]
    for thread in holders:
        thread.start()
    ready.wait()
    with pytest.raises(TimeoutError, match="'b'"), lock.lock_many(["a", "b"], timeout=0.6):
        pass
    for thread in holders:
        thread.join(5)
    assert lock.active_keys() == 0
