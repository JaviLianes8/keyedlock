from __future__ import annotations

import threading
from collections.abc import Callable

import pytest

from keyedlock import StripedLock


def _run(workers: list[Callable[[], None]]) -> None:
    threads = [threading.Thread(target=worker) for worker in workers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads)


def test_rejects_non_positive_stripe_count() -> None:
    with pytest.raises(ValueError):
        StripedLock(stripes=0)


def test_stripe_count_is_fixed_regardless_of_key_volume() -> None:
    lock = StripedLock(stripes=4)
    assert lock.stripes == 4
    for key in range(1000):
        with lock.lock(key):
            pass
    assert lock.stripes == 4


def test_a_single_stripe_serializes_every_key() -> None:
    lock = StripedLock(stripes=1)
    count = 32
    start = threading.Barrier(count)
    occupancy = {"inside": 0}
    overlaps: list[int] = []

    def worker(key: int) -> Callable[[], None]:
        def run() -> None:
            start.wait()
            with lock.lock(key):
                occupancy["inside"] += 1
                if occupancy["inside"] != 1:
                    overlaps.append(occupancy["inside"])
                occupancy["inside"] -= 1

        return run

    _run([worker(i) for i in range(count)])
    assert not overlaps


def test_keys_on_different_stripes_run_in_parallel() -> None:
    # Integer keys hash to themselves, so 0 and 1 land on distinct stripes here.
    lock = StripedLock(stripes=8)
    both_inside = threading.Barrier(2, timeout=5)
    broken: list[int] = []

    def worker(key: int) -> Callable[[], None]:
        def run() -> None:
            with lock.lock(key):
                try:
                    both_inside.wait()
                except threading.BrokenBarrierError:
                    broken.append(key)

        return run

    _run([worker(0), worker(1)])
    assert not broken


def test_reentrant_stripe_allows_nesting_on_the_same_key() -> None:
    lock = StripedLock(stripes=4, reentrant=True)
    with lock.lock("x"), lock.lock("x"):
        pass
