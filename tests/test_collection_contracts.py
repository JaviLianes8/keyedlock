"""Collection protocols preserve valid inputs, key identity and user failures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from _acquisition import Factory, exercise

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("stage", ["iter", "next"])
def test_iterator_typeerror_preserves_identity_and_message(factory: Factory, stage: str) -> None:
    failure = TypeError("explicit iterator failure")

    class Collection:
        def __iter__(self) -> Iterator[int]:
            if stage == "iter":
                raise failure
            return self

        def __next__(self) -> int:
            raise failure

    locks = factory()
    with pytest.raises(TypeError) as caught:
        exercise(locks, Collection())
    assert caught.value is failure
    assert str(caught.value) == "explicit iterator failure"
    exercise(locks, [0])


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
def test_bytearray_collection_acquires_integer_keys(factory: Factory) -> None:
    locks = factory()

    def check_count() -> None:
        if isinstance(locks, (KeyedLock, AsyncKeyedLock)):
            assert locks.active_keys() == 2

    exercise(locks, bytearray((2, 1, 2)), during=check_count)
    exercise(locks, [1, 2], during=check_count)


@pytest.mark.parametrize("factory", [KeyedLock, AsyncKeyedLock])
def test_identical_nan_keys_deduplicate_and_release(
    factory: type[KeyedLock | AsyncKeyedLock],
) -> None:
    locks = factory()
    key = float("nan")

    def check_count() -> None:
        assert locks.active_keys() == 1

    exercise(locks, [key, key, key], during=check_count)
    exercise(locks, [key], group=False, during=check_count)


@pytest.mark.parametrize("factory", [KeyedLock, AsyncKeyedLock])
@pytest.mark.parametrize("stage", ["sorting", "adjacent"])
def test_comparison_valueerror_preserves_identity_and_message(
    factory: type[KeyedLock | AsyncKeyedLock], stage: str
) -> None:
    failure = ValueError("explicit comparison failure")

    class Key(int):
        def __lt__(self, other: int) -> bool:
            if self == (2 if stage == "sorting" else 1):
                raise failure
            return bool(int.__lt__(self, other))

    locks = factory()
    with pytest.raises(ValueError) as caught:
        exercise(locks, [Key(1), Key(2)])
    assert caught.value is failure
    assert str(caught.value) == "explicit comparison failure"
    exercise(locks, [1, 2])
