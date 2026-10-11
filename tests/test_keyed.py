from __future__ import annotations

import threading
from collections.abc import Callable

from keyedlock import KeyedLock


def _run(workers: list[Callable[[], None]]) -> None:
    threads = [threading.Thread(target=worker) for worker in workers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)


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

    _run([worker] * count)
    assert not overlaps
    assert counter["value"] == count


def test_different_keys_do_not_block_each_other() -> None:
    lock = KeyedLock()
    both_inside = threading.Barrier(2, timeout=5)
    broken: list[str] = []

    def worker(key: str) -> Callable[[], None]:
        def run() -> None:
            with lock.lock(key):
                try:
                    both_inside.wait()
                except threading.BrokenBarrierError:
                    broken.append(key)

        return run

    _run([worker("a"), worker("b")])
    assert not broken


def test_table_empties_after_release() -> None:
    lock = KeyedLock()
    assert lock.active_keys() == 0
    with lock.lock("x"):
        assert lock.active_keys() == 1
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

    _run([worker(i) for i in range(count)])
    assert lock.active_keys() == 0


def test_default_lock_is_not_reentrant_but_reusable_in_sequence() -> None:
    # The default primitive is a plain, non-reentrant lock: re-entering the same key on
    # one thread would deadlock. Sequential reuse of a key is fine and leaves no residue.
    lock = KeyedLock()
    with lock.lock("x"):
        pass
    with lock.lock("x"):
        pass
    assert lock.active_keys() == 0


def test_reentrant_lock_allows_nesting_on_the_same_key() -> None:
    lock = KeyedLock(reentrant=True)
    with lock.lock("x"), lock.lock("x"):
        assert lock.active_keys() == 1
    assert lock.active_keys() == 0
