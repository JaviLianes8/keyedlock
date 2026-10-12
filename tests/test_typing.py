"""The public API is typed: mypy infers the documented types and rejects wrong ones."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

api = pytest.importorskip("mypy.api")

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock

reveal_type(KeyedLock().active_keys())
reveal_type(StripedLock().stripes)
with KeyedLock().lock("k", timeout=1.5) as held:
    reveal_type(held)
with StripedLock().lock_many([1, 2], timeout=0) as both:
    reveal_type(both)
async def main() -> None:
    async with AsyncKeyedLock().lock_many(["a"]) as acquired:
        reveal_type(acquired)
KeyedLock().lock("k", timeout="1")
StripedLock(stripes="4")
KeyedLock().lock(["unhashable"])
KeyedLock(reentrant=None)
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    out, err, _ = api.run(
        ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    )
    return str(out) + str(err)


def test_counts_are_integers(mypy_output: str) -> None:
    assert _revealed(mypy_output, 4) == "int"
    assert _revealed(mypy_output, 5) == "int"


def test_context_managers_yield_none(mypy_output: str) -> None:
    for line in (7, 9, 12):
        assert _revealed(mypy_output, line) == "None"


def test_wrong_argument_types_are_rejected(mypy_output: str) -> None:
    for line in (13, 14, 15, 16):
        assert re.search(rf"snippet\.py:{line}: error: .*\[arg-type\]", mypy_output), line


def _revealed(output: str, line: int) -> str:
    match = re.search(rf"snippet\.py:{line}: note: Revealed type is \"(.+)\"", output)
    assert match, output
    # Older mypy releases spell builtins with their module prefix.
    return match.group(1).replace("builtins.", "")
