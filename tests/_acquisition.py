"""Exercise the public acquisition methods with shared cleanup assertions."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Hashable, Iterable

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock

Factory = type[KeyedLock | StripedLock | AsyncKeyedLock]


def exercise(
    locks: KeyedLock | StripedLock | AsyncKeyedLock,
    keys: Iterable[Hashable],
    *,
    group: bool = True,
    timeout: float | None = 0,
    during: Callable[[], None] = lambda: None,
) -> None:
    try:
        if isinstance(locks, AsyncKeyedLock):

            async def run() -> None:
                manager = (
                    locks.lock_many(keys, timeout=timeout)
                    if group
                    else locks.lock(next(iter(keys)), timeout=timeout)
                )
                async with manager as held:
                    assert held is None
                    during()

            asyncio.run(run())
        else:
            manager = (
                locks.lock_many(keys, timeout=timeout)
                if group
                else locks.lock(next(iter(keys)), timeout=timeout)
            )
            with manager as held:
                assert held is None
                during()
    finally:
        if isinstance(locks, (KeyedLock, AsyncKeyedLock)):
            assert locks.active_keys() == 0
