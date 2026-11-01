"""Timeouts behave the same on every threaded lock and never leave residue."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from decimal import Decimal
from fractions import Fraction

import pytest
from _helpers import run_threads

from keyedlock import KeyedLock, StripedLock

Locker = Callable[..., AbstractContextManager[None]]


@pytest.fixture(params=["keyed", "striped"])
def locker(request: pytest.FixtureRequest) -> Iterator[Locker]:
    if request.param == "keyed":
        keyed = KeyedLock()
        yield keyed.lock
        assert keyed.active_keys() == 0
    else:
        yield StripedLock(stripes=4).lock


def _held_elsewhere(locker: Locker, key: str) -> tuple[threading.Event, threading.Thread]:
    holding, done = threading.Event(), threading.Event()

    def hold() -> None:
        with locker(key):
            holding.set()
            done.wait(10)

    thread = threading.Thread(target=hold)
    thread.start()
    assert holding.wait(5)
    return done, thread


def test_zero_timeout_fails_at_once_on_a_held_key(locker: Locker) -> None:
    done, thread = _held_elsewhere(locker, "k")
    started = time.monotonic()
    with pytest.raises(TimeoutError, match="could not lock"), locker("k", timeout=0):
        pass
    assert time.monotonic() - started < 1
    done.set()
    thread.join(5)


def test_zero_timeout_succeeds_on_a_free_key(locker: Locker) -> None:
    with locker("k", timeout=0):
        pass


def test_a_positive_timeout_waits_then_gives_up(locker: Locker) -> None:
    done, thread = _held_elsewhere(locker, "k")
    started = time.monotonic()
    with pytest.raises(TimeoutError), locker("k", timeout=0.1):
        pass
    assert time.monotonic() - started >= 0.09
    done.set()
    thread.join(5)


def test_a_timeout_is_met_when_the_holder_leaves_in_time(locker: Locker) -> None:
    done, thread = _held_elsewhere(locker, "k")
    threading.Timer(0.05, done.set).start()
    with locker("k", timeout=5):
        pass
    thread.join(5)


@pytest.mark.parametrize("bad", [-0.5, -1, math.nan])
def test_negative_or_nan_timeouts_are_rejected(locker: Locker, bad: float) -> None:
    with pytest.raises(ValueError), locker("k", timeout=bad):
        pass


@pytest.mark.parametrize("ok", [Fraction(1, 2), 0, 2])
def test_any_real_number_is_a_timeout(locker: Locker, ok: float) -> None:
    with locker("k", timeout=ok):
        pass


@pytest.mark.parametrize("bad", ["1", True, [1], 1j, Decimal("1")])
def test_non_numeric_timeouts_are_rejected(locker: Locker, bad: object) -> None:
    with pytest.raises(TypeError), locker("k", timeout=bad):
        pass


@pytest.mark.parametrize(
    "huge", [math.inf, threading.TIMEOUT_MAX * 10, pytest.param(10**400, id="huge-int")]
)
def test_timeouts_beyond_the_platform_limit_wait_without_limit(locker: Locker, huge: float) -> None:
    with locker("k", timeout=huge):
        pass


def test_timed_out_waiters_never_leak_table_entries() -> None:
    lock = KeyedLock()
    release = threading.Event()
    failures: list[int] = []

    def holder() -> None:
        with lock.lock("hot"):
            release.wait(10)

    def impatient() -> None:
        try:
            with lock.lock("hot", timeout=0.02):
                pass
        except TimeoutError:
            failures.append(1)

    hold = threading.Thread(target=holder)
    hold.start()
    run_threads([impatient] * 16)
    assert len(failures) == 16
    assert lock.active_keys() == 1
    release.set()
    hold.join(5)
    assert lock.active_keys() == 0
