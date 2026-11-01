"""Collision and built-in structure limits bound hostile key bookkeeping."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import Hashable
from contextlib import AsyncExitStack, ExitStack

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


@pytest.mark.parametrize("factory", [KeyedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
def test_collision_limit_rejects_and_cleans_up(
    factory: type[KeyedLock | AsyncKeyedLock],
    group: bool,
) -> None:
    keys = [i * sys.hash_info.modulus for i in range(65)]
    locks = factory()
    with pytest.raises(ValueError, match=r"^key hash collision limit exceeded \(64\)$"):
        if isinstance(locks, AsyncKeyedLock):

            async def run() -> None:
                async with AsyncExitStack() as stack:
                    if group:
                        await stack.enter_async_context(locks.lock_many(keys, timeout=0))
                    else:
                        for key in keys:
                            await stack.enter_async_context(locks.lock(key, timeout=0))

            asyncio.run(run())
        else:
            with ExitStack() as stack:
                if group:
                    stack.enter_context(locks.lock_many(keys, timeout=0))
                else:
                    for key in keys:
                        stack.enter_context(locks.lock(key, timeout=0))
    assert locks.active_keys() == 0


@pytest.mark.parametrize("factory", [KeyedLock, AsyncKeyedLock])
def test_collision_limit_keeps_equality_work_bounded(
    factory: type[KeyedLock | AsyncKeyedLock],
) -> None:
    comparisons = [0]

    class Key(int):
        __hash__ = int.__hash__

        def __eq__(self, other: object) -> bool:
            comparisons[0] += 1
            return bool(int.__eq__(self, other))

    locks = factory()
    keys = [Key(i * sys.hash_info.modulus) for i in range(1000)]
    with pytest.raises(ValueError, match="collision limit"):
        if isinstance(locks, AsyncKeyedLock):

            async def run() -> None:
                async with locks.lock_many(keys, timeout=0):
                    pass

            asyncio.run(run())
        else:
            with locks.lock_many(keys, timeout=0):
                pass
    assert comparisons[0] <= 5000
    assert locks.active_keys() == 0


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
def test_deep_tuple_is_rejected_without_terminating_the_process(
    factory: type[KeyedLock | StripedLock | AsyncKeyedLock],
    group: bool,
) -> None:
    program = f"""
import asyncio, os, sys
from keyedlock import {factory.__name__}
if sys.platform == 'win32':
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
key = 0
for _ in range(50000):
    key = (key,)
locks = {factory.__name__}()
manager = locks.lock_many([key], timeout=0) if {group} else locks.lock(key, timeout=0)
async def run():
    async with manager:
        pass
try:
    if {factory is AsyncKeyedLock}:
        asyncio.run(run())
    else:
        with manager:
            pass
except ValueError as error:
    assert str(error) == 'key nesting limit exceeded (64)'
    print('rejected safely', flush=True)
    os._exit(0)
os._exit(1)
"""
    env = dict(os.environ, PYTHONPATH=os.path.abspath("src"))
    result = subprocess.run(
        [sys.executable, "-c", program], env=env, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, (result.returncode, result.stderr)
    assert result.stdout.strip() == "rejected safely"


def test_nested_shared_tuples_have_a_structural_work_limit() -> None:
    key: Hashable = 0
    for _ in range(14):
        key = (key, key)
    with (
        pytest.raises(ValueError, match=r"^key structure limit exceeded \(10000\)$"),
        KeyedLock().lock(key),
    ):
        pass


@pytest.mark.parametrize("factory", [KeyedLock, AsyncKeyedLock])
def test_full_collision_bucket_allows_equal_keys_and_recovers_capacity(
    factory: type[KeyedLock | AsyncKeyedLock],
) -> None:
    keys = [i * sys.hash_info.modulus for i in range(64)]
    locks = factory()
    if isinstance(locks, AsyncKeyedLock):

        async def run() -> None:
            async with locks.lock_many([*keys, 0.0, False], timeout=0):
                assert locks.active_keys() == 64
                with pytest.raises(RuntimeError):
                    async with locks.lock(0.0, timeout=0):
                        pass
            async with locks.lock_many([key + sys.hash_info.modulus for key in keys], timeout=0):
                assert locks.active_keys() == 64

        asyncio.run(run())
    else:
        with locks.lock_many([*keys, 0.0, False], timeout=0):
            assert locks.active_keys() == 64
            with pytest.raises(RuntimeError), locks.lock(0.0, timeout=0):
                pass
        with locks.lock_many([key + sys.hash_info.modulus for key in keys], timeout=0):
            assert locks.active_keys() == 64
    assert locks.active_keys() == 0


def test_striped_keys_are_not_subject_to_the_hash_collision_limit() -> None:
    with StripedLock().lock_many([i * sys.hash_info.modulus for i in range(1000)], timeout=0):
        pass


@pytest.mark.parametrize("depth", [64, 65])
def test_tuple_nesting_limit_boundary(depth: int) -> None:
    key: Hashable = 0
    for _ in range(depth):
        key = (key,)
    if depth == 64:
        with KeyedLock().lock(key, timeout=0):
            pass
    else:
        with pytest.raises(ValueError, match="nesting limit"), KeyedLock().lock(key, timeout=0):
            pass
