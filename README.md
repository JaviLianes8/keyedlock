# keyedlock

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Lock by key: concurrent work on the same key serializes, different keys run in parallel, with reference-counted cleanup.

## Install

```
pip install keyedlock
```

Python 3.10 or newer, no dependencies.

## Usage

Serialize work per key while letting unrelated keys proceed at the same time. Use it for per-user or per-id critical sections.

```python
from concurrent.futures import ThreadPoolExecutor

from keyedlock import KeyedLock

locks = KeyedLock()
balances = {"alice": 100, "bob": 100}


def charge(user: str) -> None:
    with locks.lock(user):
        balance = balances[user]
        balances[user] = balance - 1


with ThreadPoolExecutor(8) as pool:
    for _ in range(50):
        pool.submit(charge, "alice")
        pool.submit(charge, "bob")

print(balances)  # {'alice': 50, 'bob': 50}
print(locks.active_keys())  # 0
```

Each key gets its own lock on first use. When the last holder and waiter leave, the lock
is dropped from the table, so the table never grows with the number of distinct keys you
have touched. `active_keys()` reports how many keys are held or waited on right now. A
wait that ends early (a timeout, `KeyboardInterrupt`, a cancelled task) gives its place
back too, and cleanup also attempts to recover from a key whose hash changed while held.
Keys must keep stable hashes and equality while in use. Keys follow `dict` rules: `1`, `1.0` and `True` are the same key.
Keyed tables and groups accept up to 64 unequal keys per hash. All classes reject
tuple/frozenset keys deeper than 64 levels or larger than 10,000 visited values with
`ValueError`. See the [key limits and error policy](https://github.com/JaviLianes8/keyedlock/blob/main/GUIDE.md#keys-and-ordering).

### Timeouts

Every `lock` takes `timeout`: `None` (the default) waits for ever, `0` tries once, and a
number of seconds waits at most that long. When it runs out, `TimeoutError` is raised and
nothing is left locked.

```python
from keyedlock import KeyedLock

locks = KeyedLock()
with locks.lock("report", timeout=0):
    print("acquired")  # acquired
print(locks.active_keys())  # 0
```

### Re-entry

By default the per-key lock is not reentrant. A thread that takes a key it already holds
gets `RuntimeError` straight away instead of deadlocking on itself. Pass
`reentrant=True` to allow nesting on the same key within one thread.

```python
from keyedlock import KeyedLock

plain = KeyedLock()
with plain.lock("job-42"):
    try:
        with plain.lock("job-42"):
            pass
    except RuntimeError:
        print("re-entry refused")  # re-entry refused

nested = KeyedLock(reentrant=True)
with nested.lock("job-42"), nested.lock("job-42"):
    print("nested")  # nested
```

### Several keys at once

Nested `lock` calls can deadlock when another thread takes the same keys in the
opposite order. `lock_many` deduplicates the keys and takes them in
sorted order, so every caller agrees on the order. Distinct keys must sort into a strictly
increasing order (all `str`, all `int`, ...). Incomparable pairs, such as disjoint frozen sets or a NaN
with another value, raise `TypeError` before anything is locked.
Pass a collection: a bare `str` is refused rather than split into characters.
`timeout` covers the whole acquisition, and if any key cannot be taken, the ones already
taken are released.

```python
from keyedlock import KeyedLock

locks = KeyedLock()
accounts = {"alice": 100, "bob": 0}


def transfer(source: str, target: str, amount: int) -> None:
    with locks.lock_many([source, target]):
        accounts[source] -= amount
        accounts[target] += amount


transfer("alice", "bob", 30)
transfer("bob", "alice", 10)
print(accounts)  # {'alice': 80, 'bob': 20}
```

### Striped mode

Use `StripedLock` to cap the number of locks. Unrelated keys can share a stripe and
block each other. Use `lock_many` for groups: nesting individual calls may reenter
a stripe and raise `RuntimeError`. String stripe indices depend on the process hash seed.

```python
from keyedlock import StripedLock

locks = StripedLock(stripes=256)
with locks.lock("user-7"):
    print(locks.stripes)  # 256
with locks.lock_many(["user-7", "user-9"], timeout=1):
    print("both held")  # both held
```

### asyncio

`AsyncKeyedLock` serves waiters on each key in FIFO order, including timed waiters.
Cancellation and timeout release their place. Use an instance from one event loop;
it is not thread-safe. Threaded locks make no FIFO promise.

```python
import asyncio

from keyedlock import AsyncKeyedLock

locks = AsyncKeyedLock()
log: list[str] = []


async def handle(user: str, step: str) -> None:
    async with locks.lock(user, timeout=5):
        log.append(f"{user}:{step}:start")
        await asyncio.sleep(0)
        log.append(f"{user}:{step}:end")


async def main() -> None:
    await asyncio.gather(handle("ann", "a"), handle("ann", "b"))
    async with locks.lock_many(["ann", "ben"]):
        print(locks.active_keys())  # 2


asyncio.run(main())
print(log)  # ['ann:a:start', 'ann:a:end', 'ann:b:start', 'ann:b:end']
```

## API

| Name | What it does |
| --- | --- |
| `KeyedLock(*, reentrant=False)` | One lock per key, dropped when idle. Thread-safe. |
| `KeyedLock.lock(key, *, timeout=None)` | Context manager holding `key`. |
| `KeyedLock.lock_many(keys, *, timeout=None)` | Context manager holding several keys, in sorted order. |
| `KeyedLock.active_keys()` | Keys held or waited on right now. |
| `StripedLock(stripes=64, *, reentrant=False)` | Fixed pool of locks; `stripes` is the pool size. |
| `StripedLock.lock(key, *, timeout=None)` | Context manager holding the stripe of `key`. |
| `StripedLock.lock_many(keys, *, timeout=None)` | Holds the stripes of several keys, each once, in order. |
| `AsyncKeyedLock()` | asyncio version of `KeyedLock`; `lock`, `lock_many` and `active_keys` as above. |

`lock` and `lock_many` raise `TimeoutError` when the timeout runs out, `RuntimeError` on
re-entry into a non-reentrant lock, `ValueError` for a negative or NaN timeout and
`TypeError` for a timeout that is not a real number. A timeout above
`threading.TIMEOUT_MAX` means no limit.

## Why

Python's [threading locks](https://docs.python.org/3/library/threading.html#lock-objects)
and [asyncio locks](https://docs.python.org/3/library/asyncio-sync.html#lock) protect a
single resource. They are enough when one mutex covers the work. A dictionary of those
locks can separate resources, but the application must synchronize that dictionary,
remove idle entries and arrange a consistent order for multi-key operations.

`keyedlock` supplies that bookkeeping, timeouts and an optional fixed stripe pool using
only the standard library. It is an in-process utility: it does not coordinate separate
processes or machines, provide distributed leases, or make external database updates
transactional. Use a database transaction or a process-shared lock for those needs.

The [GUIDE](https://github.com/JaviLianes8/keyedlock/blob/main/GUIDE.md) documents key
requirements, error types, deadlines and upgrade behavior. See the
[CHANGELOG](https://github.com/JaviLianes8/keyedlock/blob/main/CHANGELOG.md) for releases.
There is no command-line interface; locks are held inside the calling Python process.

MIT. See [LICENSE](https://github.com/JaviLianes8/keyedlock/blob/main/LICENSE).
