"""Numeric inputs whose conversion hooks disagree with their stored values."""

from __future__ import annotations

from fractions import Fraction
from numbers import Rational
from typing import cast


class ZeroFloatInt(int):
    def __float__(self) -> float:
        return 0.0


class IntOnlyComponent:
    def __int__(self) -> int:
        return 2


class IndexComponent:
    def __init__(self, value: int) -> None:
        self.value = value

    def __index__(self) -> int:
        return self.value


def misleading_fraction(result: float) -> float:
    class FloatOverrideFraction(Fraction):
        def __float__(self) -> float:
            return result

    return cast(float, FloatOverrideFraction(1, 2))


def misleading_comparison_fraction(method: str, result: bool) -> float:
    def compare(self: object, other: object) -> bool:
        return result

    rational = type("ComparisonFraction", (Fraction,), {method: compare})
    return cast(float, rational(1, 2))


def non_fraction_rational(*, registered: bool) -> float:
    class RegisteredRational:
        numerator = 1
        denominator = 2

        def __float__(self) -> float:
            return 0.0

    if registered:
        Rational.register(RegisteredRational)
        value = RegisteredRational()
    else:
        # Supply every abstract operation from the same ratio, without inheriting Fraction.
        half = Fraction(1, 2)
        members = {name: getattr(half, name) for name in Rational.__abstractmethods__}
        members["__float__"] = RegisteredRational.__float__
        direct = type("DirectRational", (Rational,), members)
        value = direct()
    assert isinstance(value, Rational) and not isinstance(value, Fraction)
    assert value.numerator == 1 and value.denominator == 2 and float(value) == 0.0
    return cast(float, value)


def rational_timeout(numerator: object, denominator: object) -> float:
    def get_numerator(self: object) -> object:
        return numerator

    def get_denominator(self: object) -> object:
        return denominator

    rational = type(
        "ComponentFraction",
        (Fraction,),
        {"numerator": property(get_numerator), "denominator": property(get_denominator)},
    )
    return cast(float, rational(1, 2))
