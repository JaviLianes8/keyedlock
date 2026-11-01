"""Negative hashes preserve the documented modulo collision classes."""

from __future__ import annotations

import pytest

from keyedlock import StripedLock


@pytest.mark.parametrize("stripes, negative, collision", [(3, -7, 2), (5, -11, 4), (7, -15, 6)])
@pytest.mark.parametrize("hold_many", [False, True], ids=["hold-one", "hold-many"])
@pytest.mark.parametrize("acquire_many", [False, True], ids=["acquire-one", "acquire-many"])
def test_negative_hash_collides_with_modulo_remainder(
    stripes: int, negative: int, collision: int, hold_many: bool, acquire_many: bool
) -> None:
    locks = StripedLock(stripes)
    held = locks.lock_many([negative], timeout=0) if hold_many else locks.lock(negative, timeout=0)
    with held:
        attempt = (
            locks.lock_many([collision], timeout=0)
            if acquire_many
            else locks.lock(collision, timeout=0)
        )
        with pytest.raises(RuntimeError), attempt:
            pass


@pytest.mark.parametrize("stripes, negative, distinct", [(3, -7, 1), (5, -11, 1), (7, -15, 1)])
@pytest.mark.parametrize("hold_many", [False, True], ids=["hold-one", "hold-many"])
@pytest.mark.parametrize("acquire_many", [False, True], ids=["acquire-one", "acquire-many"])
def test_negative_hash_does_not_collide_with_absolute_hash_remainder(
    stripes: int, negative: int, distinct: int, hold_many: bool, acquire_many: bool
) -> None:
    locks = StripedLock(stripes)
    held = locks.lock_many([negative], timeout=0) if hold_many else locks.lock(negative, timeout=0)
    with held:
        attempt = (
            locks.lock_many([distinct], timeout=0)
            if acquire_many
            else locks.lock(distinct, timeout=0)
        )
        with attempt:
            pass


@pytest.mark.parametrize("stripes, negative, collision", [(3, -7, 2), (5, -11, 4), (7, -15, 6)])
def test_group_deduplicates_negative_hash_modulo_collisions(
    stripes: int, negative: int, collision: int
) -> None:
    locks = StripedLock(stripes)
    with locks.lock_many([negative, collision, negative], timeout=0), locks.lock(1, timeout=0):
        pass
    with locks.lock_many(range(stripes), timeout=0):
        pass
