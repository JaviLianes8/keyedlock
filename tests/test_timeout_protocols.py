"""Numeric protocol failures have safe errors without losing explicit exceptions."""

from __future__ import annotations

import traceback
from fractions import Fraction
from typing import cast

import pytest
from _acquisition import Factory, exercise

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


def numeric_timeout(kind: str, failure: Exception | None = None) -> float:
    private = type("PRIVATE_NUMERIC_MARKER", (), {})

    def convert(self: object) -> object:
        if failure is not None:
            raise failure
        return private()

    if kind == "float":
        return cast(float, type("MalformedFloat", (float,), {"__float__": convert})(1))
    member = kind.split("_")[0]
    getter = convert
    if kind.endswith("_index"):
        index = type("MalformedIndex", (), {"__index__": convert})

        def getter(self: object) -> object:
            return index()

    rational = type("MalformedFraction", (Fraction,), {member: property(getter)})
    return cast(float, rational(1, 2))


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize(
    "kind", ["float", "numerator", "denominator", "numerator_index", "denominator_index"]
)
def test_builtin_numeric_conversion_errors_have_safe_tracebacks(
    factory: Factory, group: bool, kind: str
) -> None:
    value = numeric_timeout(kind)
    with pytest.raises(TypeError) as caught:
        exercise(factory(), [0], group=group, timeout=value)
    assert str(caught.value) == "timeout must be a real number or None (not bool)"
    assert "PRIVATE_NUMERIC_MARKER" not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize(
    "kind", ["float", "numerator", "denominator", "numerator_index", "denominator_index"]
)
@pytest.mark.parametrize("error_type", [TypeError, ValueError])
def test_explicit_numeric_conversion_exceptions_preserve_identity(
    factory: Factory, group: bool, kind: str, error_type: type[Exception]
) -> None:
    failure = error_type("explicit numeric failure")
    value = numeric_timeout(kind, failure)
    with pytest.raises(error_type) as caught:
        exercise(factory(), [0], group=group, timeout=value)
    assert caught.value is failure
    assert str(caught.value) == "explicit numeric failure"
