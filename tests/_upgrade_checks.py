"""External checks of every documented behavior change against the real PyPI release."""

from __future__ import annotations

UPGRADE = r"""
import asyncio, pickle, sys, threading
from pathlib import Path
import keyedlock
from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock

version = sys.argv[1]
assert keyedlock.__version__ == version
old = version == "0.2.0"
assert hasattr(keyedlock, "annotations") == old
classes = (KeyedLock, StripedLock, AsyncKeyedLock)
if old:
    Path("classes.pickle").write_bytes(pickle.dumps(classes))
else:
    assert pickle.loads(Path("classes.pickle").read_bytes()) == classes
for cls in classes:
    assert (cls.__module__ != "keyedlock") == old
for cls in (KeyedLock, StripedLock):
    try:
        cls(reentrant=1)
    except TypeError:
        assert not old
    else:
        assert old

bad = type("PrivateTypeName", (), {})()
for method in (lambda: StripedLock(bad), lambda: KeyedLock().lock("k", timeout=bad).__enter__()):
    try:
        method()
    except TypeError as error:
        assert ("PrivateTypeName" in str(error)) == old
    else:
        raise AssertionError("invalid type accepted")

for cls in (KeyedLock, StripedLock):
    locks = cls()
    messages = []
    def attempt():
        try:
            with locks.lock("private-key", timeout=0):
                raise AssertionError("entered")
        except TimeoutError as error:
            messages.append(str(error))
    with locks.lock("private-key"):
        worker = threading.Thread(target=attempt)
        worker.start(); worker.join(5)
        assert not worker.is_alive()
    assert len(messages) == 1
    assert ("private-key" in messages[0]) == old
    if not old and cls is StripedLock:
        assert "stripe " in messages[0]

async def main():
    locks = AsyncKeyedLock()
    async def attempt():
        try:
            async with locks.lock("private-key", timeout=0):
                raise AssertionError("entered")
        except TimeoutError as error:
            assert ("private-key" in str(error)) == old
    async with locks.lock("private-key"):
        await asyncio.create_task(attempt())
asyncio.run(main())
print("upgrade contracts ok", version)
"""
