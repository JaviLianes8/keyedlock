"""Hashability errors and collisions are independent of a key's representation."""

from __future__ import annotations

import asyncio
from collections.abc import Hashable

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
@pytest.mark.parametrize("many", [False, True])
def test_unhashable_key_errors_are_bounded(
    factory: type[KeyedLock | StripedLock], many: bool
) -> None:
    locks = factory()
    key = type("secret" * 10000, (), {"__hash__": None})()
    manager = locks.lock_many([key]) if many else locks.lock(key)
    with pytest.raises(TypeError, match=r"^key must be hashable$"), manager:
        pass
    if isinstance(locks, KeyedLock):
        assert locks.active_keys() == 0


@pytest.mark.parametrize("many", [False, True])
def test_async_unhashable_key_errors_are_bounded(many: bool) -> None:
    async def main() -> None:
        locks = AsyncKeyedLock()
        key = type("secret" * 10000, (), {"__hash__": None})()
        manager = locks.lock_many([key]) if many else locks.lock(key)
        with pytest.raises(TypeError, match=r"^key must be hashable$"):
            async with manager:
                pass
        assert locks.active_keys() == 0

    asyncio.run(main())


class Collision:
    def __hash__(self) -> int:
        return 1


def test_unequal_keys_with_identical_hashes_remain_independent() -> None:
    first, second = Collision(), Collision()
    locks = KeyedLock()
    with locks.lock(first), locks.lock(second, timeout=0):
        assert locks.active_keys() == 2
    assert locks.active_keys() == 0


def test_async_unequal_keys_with_identical_hashes_remain_independent() -> None:
    async def main() -> None:
        locks = AsyncKeyedLock()
        async with locks.lock(Collision()), locks.lock(Collision(), timeout=0):
            assert locks.active_keys() == 2
        assert locks.active_keys() == 0

    asyncio.run(main())


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
def test_user_hash_exceptions_propagate_without_rewriting(
    factory: type[KeyedLock | StripedLock],
) -> None:
    class Broken(Hashable):
        def __hash__(self) -> int:
            raise LookupError("user failure")

    with pytest.raises(LookupError, match="user failure"), factory().lock(Broken()):
        pass
