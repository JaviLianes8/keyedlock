from __future__ import annotations

import threading
from collections.abc import Callable

import pytest
from _helpers import run_threads

from keyedlock import StripedLock


@pytest.mark.parametrize("bad", [0, -3])
def test_rejects_non_positive_stripe_count(bad: int) -> None:
    with pytest.raises(ValueError):
        StripedLock(stripes=bad)


@pytest.mark.parametrize("bad", [4.0, "4", True])
def test_rejects_a_non_integer_stripe_count(bad: object) -> None:
    with pytest.raises(TypeError):
        StripedLock(stripes=bad)  # type: ignore[arg-type]


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

    run_threads([worker(i) for i in range(count)])
    assert not overlaps


def test_keys_on_different_stripes_run_in_parallel() -> None:
    # Integer keys hash to themselves, so 0 and 1 land on distinct stripes here.
    lock = StripedLock(stripes=8)
    both_inside = threading.Barrier(2, timeout=5)

    def worker(key: int) -> Callable[[], None]:
        def run() -> None:
            with lock.lock(key):
                both_inside.wait()

        return run

    run_threads([worker(0), worker(1)])


def test_an_exception_in_the_body_releases_the_stripe() -> None:
    lock = StripedLock(stripes=2)
    with pytest.raises(KeyError), lock.lock("x"):
        raise KeyError("boom")
    with lock.lock("x", timeout=0):
        pass


def test_negative_hashes_map_to_a_valid_stripe() -> None:
    lock = StripedLock(stripes=3)
    with lock.lock(-7), lock.lock(-8):
        pass
