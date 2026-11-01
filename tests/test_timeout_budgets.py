"""Normalized numeric magnitudes reach the real acquisition boundaries."""

from __future__ import annotations

import math
import threading
from fractions import Fraction
from types import SimpleNamespace
from typing import cast

import pytest
from _acquisition import Factory, exercise
from _timeout_values import (
    IndexComponent,
    ZeroFloatInt,
    misleading_comparison_fraction,
    misleading_fraction,
    non_fraction_rational,
    rational_timeout,
)

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock, _fifo, _primitive, _timing


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(ZeroFloatInt(2), 2.0, id="integer-subclass"),
        pytest.param(cast(float, Fraction(1, 2)), 0.5, id="fraction-half"),
        pytest.param(cast(float, Fraction(3, 2)), 1.5, id="fraction-three-halves"),
        pytest.param(cast(float, Fraction(0, 1)), 0.0, id="fraction-zero"),
        pytest.param(rational_timeout(0, -2), 0.0, id="zero-negative-denominator"),
        pytest.param(rational_timeout(-1, -2), 0.5, id="two-negative-components"),
        pytest.param(rational_timeout(IndexComponent(1), 2), 0.5, id="numerator-index"),
        pytest.param(rational_timeout(1, IndexComponent(2)), 0.5, id="denominator-index"),
        pytest.param(cast(float, Fraction(10**400, 1)), None, id="huge-fraction"),
        pytest.param(
            cast(float, Fraction(10**400 + 1, 2 * 10**400 + 1)),
            0.5,
            id="finite-ratio-huge-components",
        ),
        pytest.param(misleading_fraction(0.0), 0.5, id="fraction-float-zero"),
        pytest.param(misleading_fraction(-1.0), 0.5, id="fraction-float-negative"),
        pytest.param(misleading_fraction(2.0), 0.5, id="fraction-float-positive"),
        pytest.param(misleading_fraction(math.inf), 0.5, id="fraction-float-infinity"),
        pytest.param(misleading_fraction(math.nan), 0.5, id="fraction-float-nan"),
        *(
            pytest.param(
                misleading_comparison_fraction(method, result),
                0.5,
                id=f"fraction-{method.strip('_')}-{result}",
            )
            for method in ("__lt__", "__le__", "__eq__", "__ne__", "__gt__", "__ge__")
            for result in (False, True)
        ),
        pytest.param(non_fraction_rational(registered=False), 0.5, id="direct-rational"),
        pytest.param(non_fraction_rational(registered=True), 0.5, id="registered-rational"),
        pytest.param(cast(float, Fraction(1, 10**400)), 0.0, id="positive-rational-underflow"),
        pytest.param(
            cast(float, Fraction(int(threading.TIMEOUT_MAX), 1)),
            threading.TIMEOUT_MAX,
            id="fraction-maximum",
        ),
        pytest.param(
            cast(float, Fraction(2 * int(threading.TIMEOUT_MAX), 1)),
            None,
            id="fraction-representable-above-maximum",
        ),
        pytest.param(threading.TIMEOUT_MAX, threading.TIMEOUT_MAX, id="maximum"),
        pytest.param(int(threading.TIMEOUT_MAX), threading.TIMEOUT_MAX, id="integer-maximum"),
        pytest.param(math.nextafter(threading.TIMEOUT_MAX, math.inf), None, id="above-maximum"),
        pytest.param(int(threading.TIMEOUT_MAX) + 1, None, id="integer-above-maximum"),
    ],
)
def test_numeric_timeout_budget_reaches_acquisition(
    factory: Factory,
    group: bool,
    value: float,
    expected: float | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    budgets: list[float | None] = []
    acquire = _primitive.Slot.acquire
    async_acquire = _fifo.FifoLock.acquire

    def observed_acquire(slot: _primitive.Slot, timeout: float | None) -> bool:
        budgets.append(timeout)
        return acquire(slot, 0)

    async def observed_async_acquire(lock: _fifo.FifoLock, timeout: float | None) -> bool:
        budgets.append(timeout)
        return await async_acquire(lock, 0)

    monkeypatch.setattr(_timing, "time", SimpleNamespace(monotonic=lambda: 100.0))
    monkeypatch.setattr(_primitive.Slot, "acquire", observed_acquire)
    monkeypatch.setattr(_fifo.FifoLock, "acquire", observed_async_acquire)
    exercise(factory(), [0, 1], group=group, timeout=value)
    assert budgets == [expected] * (2 if group else 1)
