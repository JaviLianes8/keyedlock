"""Keys that change or misbehave while held never leave a dead entry behind."""

from __future__ import annotations

import asyncio

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock


class Shifty:
    """A key whose hash changes after it is taken, as a mutated key's would."""

    def __init__(self) -> None:
        self.value = 1

    def __hash__(self) -> int:
        return self.value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Shifty) and other.value == self.value


def test_a_key_mutated_while_held_is_still_cleaned_up() -> None:
    lock = KeyedLock()
    key = Shifty()
    with lock.lock("other"), pytest.raises(KeyError, match="body"), lock.lock(key):
        key.value = 2
        raise KeyError("body")  # the body's exception is the one that surfaces
    assert lock.active_keys() == 0


def test_a_mutated_key_is_cleaned_up_in_the_async_lock() -> None:
    async def main() -> None:
        lock = AsyncKeyedLock()
        key = Shifty()
        async with lock.lock(key):
            key.value = 2
        assert lock.active_keys() == 0

    asyncio.run(main())
