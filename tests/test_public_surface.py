"""Pin constructor defaults, signatures, context results and public documentation."""

from __future__ import annotations

import doctest
import inspect
import pickle
from typing import get_type_hints

import keyedlock
from keyedlock import AsyncKeyedLock, KeyedLock, StripedLock


def test_every_public_class_and_method_has_a_passing_example() -> None:
    count = 0
    for name in keyedlock.__all__:
        cls = getattr(keyedlock, name)
        objects = [cls, *(getattr(cls, n) for n in vars(cls) if not n.startswith("_"))]
        for obj in objects:
            doc = inspect.getdoc(obj)
            assert doc is not None and ">>>" in doc
            test = doctest.DocTestParser().get_doctest(doc, {}, name, None, 0)
            runner = doctest.DocTestRunner()
            runner.run(test)
            assert runner.failures == 0
            count += runner.tries
        assert pickle.loads(pickle.dumps(cls)) is cls
        assert cls.__module__ == "keyedlock"
    assert count >= 30


def test_public_signatures_and_annotations_are_stable() -> None:
    assert str(inspect.signature(KeyedLock)) == "(*, reentrant: 'bool' = False) -> 'None'"
    assert str(inspect.signature(StripedLock)) == (
        "(stripes: 'int' = 64, *, reentrant: 'bool' = False) -> 'None'"
    )
    assert str(inspect.signature(AsyncKeyedLock)) == "() -> 'None'"
    for cls in (KeyedLock, StripedLock, AsyncKeyedLock):
        for name in ("lock", "lock_many"):
            method = getattr(cls, name)
            parameters = inspect.signature(method).parameters
            assert list(parameters) == ["self", "key" if name == "lock" else "keys", "timeout"]
            assert parameters["timeout"].kind is inspect.Parameter.KEYWORD_ONLY
            assert parameters["timeout"].default is None
            assert get_type_hints(method)["timeout"] == float | None


def test_sync_contexts_yield_none_and_empty_batches_work() -> None:
    for locks in (KeyedLock(), StripedLock()):
        with locks.lock("k") as held:
            assert held is None
        with locks.lock_many(["a", "b"]) as many:
            assert many is None
        with locks.lock_many([]) as empty:
            assert empty is None


def test_stripes_is_read_only_and_defaults_to_64() -> None:
    import pytest

    locks = StripedLock()
    assert locks.stripes == 64
    with pytest.raises(AttributeError):
        locks.stripes = 3  # type: ignore[misc]
