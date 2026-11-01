"""Numeric inputs whose conversion hooks disagree with their stored values."""

from __future__ import annotations


class ZeroFloatInt(int):
    def __float__(self) -> float:
        return 0.0
