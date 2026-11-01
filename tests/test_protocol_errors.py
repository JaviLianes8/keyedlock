"""Malformed built-in protocols have bounded errors across every entry point."""

from __future__ import annotations

import asyncio
import traceback
from collections.abc import Hashable
from typing import cast

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock

Factory = type[KeyedLock | StripedLock | AsyncKeyedLock]


def enter(factory: Factory, value: object, group: bool) -> None:
    locks = factory()
    if isinstance(locks, AsyncKeyedLock):

        async def run() -> None:
            manager = locks.lock_many(value) if group else locks.lock(value)  # type: ignore[arg-type]
            async with manager:
                pass

        asyncio.run(run())
    else:
        manager = locks.lock_many(value) if group else locks.lock(value)  # type: ignore[arg-type]
        with manager:
            pass


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("group", [False, True])
@pytest.mark.parametrize("kind", ["tuple", "memoryview", "nested_memoryview"])
def test_builtin_unhashability_has_a_safe_complete_traceback(
    factory: Factory,
    group: bool,
    kind: str,
) -> None:
    private = type("PRIVATE_TYPE_MARKER", (), {"__hash__": None})
    key: object = {
        "tuple": (private(),),
        "memoryview": memoryview(bytearray(b"x")),
        "nested_memoryview": (memoryview(bytearray(b"x")),),
    }[kind]
    with pytest.raises(TypeError, match=r"^key must be hashable$") as caught:
        enter(factory, [key] if group else key, group)
    assert "PRIVATE_TYPE_MARKER" not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
def test_noniterable_collection_has_a_safe_complete_traceback(factory: Factory) -> None:
    private = type("PRIVATE_TYPE_MARKER", (), {})
    with pytest.raises(TypeError, match=r"^keys must be an iterable of keys$") as caught:
        enter(factory, private(), True)
    assert "PRIVATE_TYPE_MARKER" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize("factory", [KeyedLock, AsyncKeyedLock])
def test_incomparable_keys_have_a_safe_complete_traceback(factory: Factory) -> None:
    private = type("PRIVATE_TYPE_MARKER", (), {})
    with pytest.raises(TypeError, match="total order") as caught:
        enter(factory, [private(), private()], True)
    assert "PRIVATE_TYPE_MARKER" not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("factory", [KeyedLock, AsyncKeyedLock])
def test_comparison_typeerrors_are_normalized_without_a_displayed_chain(factory: Factory) -> None:
    class ComparisonError(TypeError):
        pass

    class Key:
        def __lt__(self, other: object) -> bool:
            raise ComparisonError("private comparison failure")

    with pytest.raises(TypeError, match="total order") as caught:
        enter(factory, [Key(), Key()], True)
    assert type(caught.value) is TypeError
    assert "ComparisonError:" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
@pytest.mark.parametrize("error", [TypeError("user hash"), ValueError("user hash")])
def test_nested_user_hash_errors_preserve_identity(factory: Factory, error: Exception) -> None:
    class Key:
        def __hash__(self) -> int:
            raise error

    with pytest.raises(type(error)) as caught:
        enter(factory, (Key(),), False)
    assert caught.value is error


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock, AsyncKeyedLock])
def test_readonly_memoryview_is_a_valid_key(factory: Factory) -> None:
    enter(factory, cast(Hashable, memoryview(b"x")), False)
