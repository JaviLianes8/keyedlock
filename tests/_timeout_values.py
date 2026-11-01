"""Numeric inputs whose conversion hooks disagree with their stored values."""

from __future__ import annotations

from fractions import Fraction
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
