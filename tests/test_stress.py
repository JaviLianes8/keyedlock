"""Many threads, few keys, mixed timeouts, failures and multi-key locks: the invariants hold."""

from __future__ import annotations

import random
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager

import pytest
from _helpers import run_threads

from keyedlock import KeyedLock, StripedLock

THREADS = 48
ROUNDS = 150
KEYS = 6


@pytest.fixture(autouse=True)
def _fast_switching() -> Iterator[None]:
    # Switch threads far more often than the default 5 ms so races actually interleave.
    previous = sys.getswitchinterval()
    sys.setswitchinterval(1e-5)
    yield
    sys.setswitchinterval(previous)


class Ledger:
    """Records who is inside each key; only correct if the lock really excludes."""

    def __init__(self) -> None:
        self.inside = [0] * KEYS
        self.totals = [0] * KEYS
        self.overlaps = 0
        self.peak_keys = 0
        self._meta = threading.Lock()
        self._busy: set[int] = set()

    def enter(self, keys: list[int]) -> None:
        for key in keys:
            self.inside[key] += 1
            if self.inside[key] != 1:
                self.overlaps += 1
            total = self.totals[key]
            time.sleep(0)  # widen the read-modify-write window
            self.totals[key] = total + 1
        with self._meta:
            self._busy.update(keys)
            self.peak_keys = max(self.peak_keys, len(self._busy))
        time.sleep(0)
        with self._meta:
            self._busy.difference_update(keys)
        for key in keys:
            self.inside[key] -= 1


def _hammer(
    lock_one: Callable[..., AbstractContextManager[None]],
    lock_many: Callable[..., AbstractContextManager[None]],
) -> tuple[Ledger, list[int]]:
    ledger = Ledger()
    expected = [[0] * KEYS for _ in range(THREADS)]

    def worker(seed: int) -> Callable[[], None]:
        rng = random.Random(seed)

        def run() -> None:
            mine = expected[seed]
            for _ in range(ROUNDS):
                keys = rng.sample(range(KEYS), rng.choice((1, 1, 1, 2, 3)))
                timeout = rng.choice((None, None, 0, 0.001, 0.01))
                fail = rng.random() < 0.1
                manager = (
                    lock_one(keys[0], timeout=timeout)
                    if len(keys) == 1
                    else lock_many(keys, timeout=timeout)
                )
                try:
                    with manager:
                        ledger.enter(keys)
                        for key in keys:
                            mine[key] += 1
                        if fail:
                            raise ValueError("work failed")
                except (TimeoutError, ValueError):
                    pass

        return run

    run_threads([worker(seed) for seed in range(THREADS)], timeout=120)
    return ledger, [sum(row[key] for row in expected) for key in range(KEYS)]


def test_keyed_lock_invariants_under_contention() -> None:
    lock = KeyedLock()
    ledger, expected = _hammer(lock.lock, lock.lock_many)
    assert ledger.overlaps == 0
    assert ledger.totals == expected
    assert sum(expected) > THREADS * ROUNDS // 4  # plenty of real entries happened
    assert ledger.peak_keys > 1  # distinct keys really ran side by side
    assert lock.active_keys() == 0


def test_striped_lock_invariants_under_contention() -> None:
    lock = StripedLock(stripes=KEYS)  # small int keys: one stripe each
    ledger, expected = _hammer(lock.lock, lock.lock_many)
    assert ledger.overlaps == 0
    assert ledger.totals == expected
    assert ledger.peak_keys > 1
