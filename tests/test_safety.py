"""Public error paths do not format keys or caller-controlled type names."""

from __future__ import annotations

import asyncio
import threading

import pytest

from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


class SecretKey:
    def __repr__(self) -> str:
        raise AssertionError("a key representation must never be requested")


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
@pytest.mark.parametrize("key", [SecretKey(), "secret" * 200000], ids=["object", "long-str"])
def test_thread_timeout_never_formats_keys(
    factory: type[KeyedLock | StripedLock], key: object
) -> None:
    locks = factory()
    errors: list[BaseException] = []

    def attempt() -> None:
        try:
            with locks.lock(key, timeout=0):
                raise AssertionError("entered a held key")
        except BaseException as error:
            errors.append(error)

    with locks.lock(key):
        worker = threading.Thread(target=attempt, daemon=True)
        worker.start()
        worker.join(5)
        assert not worker.is_alive()
    assert len(errors) == 1
    assert type(errors[0]) is TimeoutError
    assert len(str(errors[0])) < 100
    assert "secret" not in str(errors[0])


@pytest.mark.parametrize("key", [SecretKey(), "secret" * 200000], ids=["object", "long-str"])
def test_async_timeout_never_formats_keys(key: object) -> None:
    async def main() -> None:
        locks = AsyncKeyedLock()

        async def attempt() -> None:
            with pytest.raises(TimeoutError) as caught:
                async with locks.lock(key, timeout=0):
                    pytest.fail("entered a held key")
            assert str(caught.value) == "could not lock key within 0.0 seconds"

        async with locks.lock(key):
            await asyncio.create_task(attempt())
        assert locks.active_keys() == 0

    asyncio.run(main())


@pytest.mark.parametrize("factory", [KeyedLock, StripedLock])
@pytest.mark.parametrize("bad", [0, 1, None, "secret" * 1000])
def test_reentrant_requires_a_bool(factory: type[KeyedLock | StripedLock], bad: object) -> None:
    with pytest.raises(TypeError, match=r"^reentrant must be a bool$"):
        factory(reentrant=bad)  # type: ignore[arg-type]


def test_long_type_names_are_not_echoed() -> None:
    bad = type("secret" * 20000, (), {})()
    with pytest.raises(TypeError) as stripes:
        StripedLock(bad)
    with pytest.raises(TypeError) as timeout, KeyedLock().lock("k", timeout=bad):
        pass
    assert len(str(stripes.value)) < 100
    assert len(str(timeout.value)) < 100
