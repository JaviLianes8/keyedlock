# keyedlock guide

## Scope and API

Import `KeyedLock`, `StripedLock` and `AsyncKeyedLock` from `keyedlock`.
`__all__` contains those three classes. `__version__` is the release string.
Private modules are implementation details. There is no CLI.

`KeyedLock(*, reentrant=False)` uses a separate mutex for each active key.
`StripedLock(stripes=64, *, reentrant=False)` uses a fixed pool, selecting
`hash(key) % stripes`. Its read-only `stripes` property reports the pool size.
Both synchronize threads in one process. `reentrant` must be a boolean;
`stripes` must be an integer of at least one, excluding booleans.

`AsyncKeyedLock()` synchronizes tasks in one event loop. It is not thread-safe.
Share the instance among tasks, but do not move it between active loops. It has no
reentrant mode. Cancellation of a holder releases its locks as the context exits;
cancellation of a waiter removes its queue entry, including during handoff.

All three offer `lock(key, *, timeout=None)` and
`lock_many(keys, *, timeout=None)`. These return fresh, single-use context managers;
entering them yields `None`. Acquisition and validation happen on entry, not when
the context manager is created. Exceptions from the body propagate after cleanup.
Use `with` for thread locks and `async with` for async locks. Keep the context's
entry and exit in the same thread or task.

`KeyedLock.active_keys()` and `AsyncKeyedLock.active_keys()` count distinct keys
with a holder or waiter. They return zero when idle. Counts are snapshots, not a
way to decide whether a later acquisition will block. Striped locks retain their
fixed pool even when idle and do not provide `active_keys()`.

```python
from keyedlock import KeyedLock, StripedLock

locks = KeyedLock()
with locks.lock_many([2, 1, 2]) as held:
    print(held, locks.active_keys())  # None 2
print(locks.active_keys())  # 0
print(StripedLock().stripes)  # 64
```

## Keys and ordering

Keys follow dictionary hash and equality semantics. For example, `1`, `1.0` and
`True` identify the same key. Hash collisions alone do not merge unequal keys in
`KeyedLock` or `AsyncKeyedLock`. In `StripedLock`, collisions in stripe indices
intentionally share a mutex, even for unequal keys.

Supply hashable keys with stable, non-raising hash and equality operations.
Mutating a key while held violates this requirement: cleanup attempts to recover,
but such keys cannot be relied on for exclusion. User-defined key operations and
iterables can execute arbitrary code; their exceptions propagate and their execution
time is not bounded by this library.

`lock_many` consumes the iterable before acquiring anything, deduplicates keys,
sorts them and checks each adjacent pair is strictly increasing. The caller must
provide a consistent total order. Incomparable pairs raise `TypeError`; a singleton
does not need a comparison. Text and bytes passed as the entire collection are
rejected. An empty iterable succeeds and holds nothing, after validating timeout.
For striped locks, only stripe indices are sorted; mixed key types are fine.

Use one `lock_many` call to acquire a group. Its ordering prevents cycles between
otherwise unnested group acquisitions on the same instance. It cannot prevent
cycles caused by previously held keys, another lock instance, or other resources.
Reentering a non-reentrant key or stripe from its owner raises `RuntimeError`.

## Timeouts and errors

`None` waits indefinitely; zero tries immediately; a positive real number is seconds.
Booleans, complex numbers, strings and `Decimal` are rejected. Integers and
`Fraction` values work at runtime; the static annotation is `float | None`, which
also accepts integers in type checkers. NaN and negative values raise `ValueError`.
Above `threading.TIMEOUT_MAX`, including infinity and enormous positive integers,
the timeout means no limit. This is a library policy, not the standard library's
overflow behavior.

For a group, one monotonic deadline is created before consuming the iterable and
shared by all acquisitions. Each acquisition gets the remaining budget, floored at
zero. A free lock can succeed with zero remaining budget. Timeouts do not interrupt
work inside a successful context or user-defined iterable/key operations.

| Exception | Condition |
| --- | --- |
| `TypeError` | Invalid option type, unhashable key, text collection or incomparable keys. |
| `ValueError` | Negative or NaN timeout; non-positive stripe count. |
| `TimeoutError` | Acquisition could not complete within its remaining budget. |
| `RuntimeError` | Same owner reenters a non-reentrant key or stripe. |
| `asyncio.CancelledError` | The caller cancels the waiting or holding task. |

Library-generated messages never format a key or caller-controlled type name.
Timeout messages include the normalized timeout in seconds; striped errors also
include a stripe index. Messages from user code, including key methods and the body,
are not rewritten. Prefer catching the documented error families to matching text.

Threaded locks make no FIFO promise, matching `threading.Lock`.
Async waiters on one key are FIFO, including waiters with positive timeouts.
Zero-timeout newcomers cannot overtake queued waiters. Cancelled or expired waiters
lose their place.

## Upgrading from 0.2.0

Install `keyedlock==1.0.0` over 0.2.0 with pip. Names, signatures, defaults, key
semantics, return values, fairness and built-in error families remain unchanged.
Use actual booleans for `reentrant`, and update any assertions of error text:
keys and arbitrary type names are no longer echoed. Public class `__module__`
is now `keyedlock`; old pickled class references still resolve. Instances contain
live synchronization state and are not promised to be pickleable.
The async queue now avoids scans on handoff and cancellation.

## Validation and sources

The source distribution includes tests. Install the `dev` extra, then run
`ruff format --check .`, `ruff check .`, `mypy --strict src tests` and
`python -m pytest --basetemp=<scratch-directory>`.
Every test has a 300-second timeout. Set `KEYEDLOCK_E2E=1` for wheel build,
installation and real consumer checks; `KEYEDLOCK_E2E_PYPI=1` also checks the
upgrade from PyPI 0.2.0.

The reference tests execute `asyncio.Lock`, `threading.RLock` and `dict` as
independent oracles. Their authored schedules are seeded and reproducible.
The Python v3.14.0 documentation was fetched on 2026-11-01:

- [Threading](https://github.com/python/cpython/blob/v3.14.0/Doc/library/threading.rst)
- [Async synchronization](https://github.com/python/cpython/blob/v3.14.0/Doc/library/asyncio-sync.rst)
- [Built-in types](https://github.com/python/cpython/blob/v3.14.0/Doc/library/stdtypes.rst)

`tests/upstream/MANIFEST.json` records URLs, revision, sizes, hashes and license.
`python scripts/fetch_upstream.py <scratch-directory>` refetches those exact files.
Set `KEYEDLOCK_UPSTREAM` to that directory to verify them in the suite; the
provenance test skips when it is unset. No copied specification text ships.
