"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with KEYEDLOCK_E2E=1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("KEYEDLOCK_E2E") != "1", reason="set KEYEDLOCK_E2E=1 to build and install"
)

PROGRAM = r"""
import asyncio, importlib.metadata, importlib.resources, threading
import keyedlock
from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock

assert "site-packages" in keyedlock.__file__, keyedlock.__file__
assert importlib.metadata.version("keyedlock") == keyedlock.__version__
assert importlib.resources.files("keyedlock").joinpath("py.typed").is_file()

locks = KeyedLock()
totals = {"a": 0, "b": 0}
def work(key):
    for _ in range(200):
        with locks.lock(key):
            value = totals[key]
            totals[key] = value + 1
threads = [threading.Thread(target=work, args=(k,)) for k in "ab" * 8]
for t in threads: t.start()
for t in threads: t.join()
assert totals == {"a": 1600, "b": 1600}, totals
assert locks.active_keys() == 0

def _try(lock):
    try:
        with lock.lock("x", timeout=0.01):
            return "entered"
    except TimeoutError:
        return "timeout"
with locks.lock("x"):
    try:
        with locks.lock("x"):
            raise AssertionError("re-entered")
    except RuntimeError:
        pass
    seen = []
    t = threading.Thread(target=lambda: seen.append(_try(locks)))
    t.start(); t.join()
assert seen == ["timeout"], seen
with locks.lock_many(["b", "a", "a"], timeout=1):
    assert locks.active_keys() == 2
assert locks.active_keys() == 0

striped = StripedLock(stripes=1)
with striped.lock_many(["p", "q"]):
    pass

async def main():
    alock = AsyncKeyedLock()
    order = []
    async def job(n):
        async with alock.lock("k", timeout=5):
            order.append(n)
            await asyncio.sleep(0)
    await asyncio.gather(*(job(n) for n in range(5)))
    assert order == [0, 1, 2, 3, 4], order
    assert alock.active_keys() == 0
asyncio.run(main())
print("e2e ok")
"""


def _run(*cmd: str | Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--wheel", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("keyedlock-*.whl")

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "e2e ok"
