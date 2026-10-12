from __future__ import annotations

import threading
from collections.abc import Callable

import pytest
from _helpers import run_threads

from keyedlock import KeyedLock


def test_same_key_serializes_concurrent_work() -> None:
    lock = KeyedLock()
    count = 32
    start = threading.Barrier(count)
    occupancy = {"inside": 0}
    overlaps: list[int] = []
    counter = {"value": 0}

    def worker() -> None:
        start.wait()
        with lock.lock("shared"):
            occupancy["inside"] += 1
            if occupancy["inside"] != 1:
                overlaps.append(occupancy["inside"])
            # Non-atomic read-modify-write: it only lands all updates if serialized.
            counter["value"] = counter["value"] + 1
            occupancy["inside"] -= 1

    run_threads([worker] * count)
    assert not overlaps
    assert counter["value"] == count


def test_different_keys_do_not_block_each_other() -> None:
    lock = KeyedLock()
    both_inside = threading.Barrier(2, timeout=5)

    def worker(key: str) -> Callable[[], None]:
        def run() -> None:
            with lock.lock(key):
                both_inside.wait()

        return run

    run_threads([worker("a"), worker("b")])


def test_equal_keys_share_one_lock() -> None:
    lock = KeyedLock()
    with lock.lock(1), pytest.raises(TimeoutError):
        # 1.0 == 1 and hash(1.0) == hash(1): dict rules make them the same key.
        run_on_other_thread(lambda: lock.lock(1.0, timeout=0).__enter__())


def run_on_other_thread(action: Callable[[], object]) -> None:
    errors: list[BaseException] = []

    def target() -> None:
        try:
            action()
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(10)
    if errors:
        raise errors[0]


def test_table_empties_after_release() -> None:
    lock = KeyedLock()
    assert lock.active_keys() == 0
    with lock.lock("x"):
        assert lock.active_keys() == 1
    assert lock.active_keys() == 0


def test_a_waiter_inherits_the_key_and_then_cleans_up() -> None:
    lock = KeyedLock()
    entered = threading.Event()

    def waiter() -> None:
        with lock.lock("x"):
            entered.set()

    with lock.lock("x"):
        thread = threading.Thread(target=waiter)
        thread.start()
        assert not entered.wait(0.05)
        assert lock.active_keys() == 1
    thread.join(5)
    assert entered.is_set()
    assert lock.active_keys() == 0


def test_table_empties_after_concurrent_use() -> None:
    lock = KeyedLock()
    count = 24
    start = threading.Barrier(count)

    def worker(key: int) -> Callable[[], None]:
        def run() -> None:
            start.wait()
            with lock.lock(key % 4):
                pass

        return run

    run_threads([worker(i) for i in range(count)])
    assert lock.active_keys() == 0


def test_an_exception_in_the_body_releases_the_key() -> None:
    lock = KeyedLock()
    with pytest.raises(KeyError), lock.lock("x"):
        raise KeyError("boom")
    assert lock.active_keys() == 0
    with lock.lock("x", timeout=0):
        pass


def test_an_unhashable_key_is_rejected_without_residue() -> None:
    lock = KeyedLock()
    with pytest.raises(TypeError), lock.lock(["not", "hashable"]):  # type: ignore[arg-type]
        pass
    assert lock.active_keys() == 0


def test_an_interrupted_wait_gives_its_reference_back(monkeypatch: pytest.MonkeyPatch) -> None:
    # KeyboardInterrupt can land inside acquire(); the key must not stay in the table.
    from keyedlock import _keyed

    def interrupted(self: object, timeout: float | None) -> bool:
        raise KeyboardInterrupt

    lock = KeyedLock()
    monkeypatch.setattr(_keyed._Entry, "acquire", interrupted)
    with pytest.raises(KeyboardInterrupt), lock.lock("x"):
        pass
    assert lock.active_keys() == 0


def test_sequential_reuse_leaves_no_residue() -> None:
    lock = KeyedLock()
    with lock.lock("x"):
        pass
    with lock.lock("x"):
        pass
    assert lock.active_keys() == 0
