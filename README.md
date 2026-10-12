# keyedlock

Lock by key: concurrent work on the same key serializes, different keys run in parallel, with reference-counted cleanup.

## Install

```
pip install keyedlock
```

Python 3.10 or newer, no dependencies.

## Usage

Serialize work per key while letting unrelated keys proceed at the same time. A common
case is a per-user or per-id critical section: two requests for the same user wait for
each other, two requests for different users do not.

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
back too, and so does a key whose hash changed while it was held. Keys follow `dict` rules: `1`, `1.0` and `True` are the same key.

### Timeouts

Every `lock` takes `timeout`: `None` (the default) waits for ever, `0` tries once, and a
number of seconds waits at most that long. When it runs out, `TimeoutError` is raised and
nothing is left locked.

```python
import threading

from keyedlock import KeyedLock

locks = KeyedLock()
holding = threading.Event()
done = threading.Event()


def slow_job() -> None:
    with locks.lock("report"):
        holding.set()
        done.wait()


worker = threading.Thread(target=slow_job)
worker.start()
holding.wait()
try:
    with locks.lock("report", timeout=0.05):
        pass
except TimeoutError as error:
    print(error)  # could not lock key 'report' within 0.05 seconds
done.set()
worker.join()
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

Taking two keys by nesting `lock` calls deadlocks as soon as another thread takes the
same pair in the opposite order. `lock_many` deduplicates the keys and takes them in
sorted order, so every caller agrees on the order. The keys need a total order (all
`str`, all `int`, ...); sets, NaN and mixed types raise `TypeError` before anything is
locked. Pass a collection: a bare `str` is refused rather than split into characters.
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

When the key space is huge or unbounded and you would rather cap memory than track every
key, use `StripedLock`. It maps keys onto a fixed pool of locks: memory is allocated once
and never grows, at the cost of occasional false contention when two unrelated keys land
on the same stripe. Because of that, nest two keys with `lock_many`, not with two
`lock` calls: two different keys may share a stripe (with string keys, which ones depends
on the process hash seed), and re-entering a held stripe raises `RuntimeError`.

```python
from keyedlock import StripedLock

locks = StripedLock(stripes=256)
with locks.lock("user-7"):
    print(locks.stripes)  # 256
with locks.lock_many(["user-7", "user-9"], timeout=1):
    print("both held")  # both held
```

### asyncio

`AsyncKeyedLock` gives coroutines the same contract. Waiters on one key are served first
come, first served, whether or not they pass a timeout: the lock is handed straight to
the oldest waiter, so nobody can slip past the queue. A task cancelled or timed out while
waiting leaves nothing behind. Like `asyncio.Lock`, it is not thread-safe: use an
instance from one event loop.

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

### Fairness

`KeyedLock` and `StripedLock` sit on `threading.Lock`, whose documentation leaves the
order in which waiters are woken undefined; under sustained contention on one key a
waiter can be overtaken. `AsyncKeyedLock` is strictly first come, first served.

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

The "one lock per key" pattern is re-implemented constantly: a dict of locks guarded by a
meta-lock. Done naively the dict leaks, growing with every distinct key ever seen; done
carefully the reference counting is easy to get wrong under contention, timeouts and
interruption.

Existing options fall short. `mutexcache` creates a lock per key but keeps it forever, so
the table grows without bound. Per-key helpers like the one inside `fleche` are not
standalone packages. There is no small, typed, zero-dependency library that pairs
reference-counted cleanup with timeouts, deadlock-free multi-key locking, an asyncio
variant and an optional striped mode. `keyedlock` is that: standard library only, full
type hints, `py.typed`, and `mypy --strict` clean.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
