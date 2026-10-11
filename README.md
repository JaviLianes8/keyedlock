# keyedlock

Lock by key: concurrent work on the same key serializes, different keys run in parallel, with reference-counted cleanup.

## Install

```
pip install keyedlock
```

## Usage

Serialize work per key while letting unrelated keys proceed at the same time. A common
case is a per-user or per-id critical section: two requests for the same user wait for
each other, two requests for different users do not.

```python
from keyedlock import KeyedLock

locks = KeyedLock()

def charge(user_id: str) -> None:
    with locks.lock(user_id):
        balance = read_balance(user_id)
        write_balance(user_id, balance - 1)
```

Each key gets its own lock on first use. When the last holder and waiter leave, the lock
is dropped from the table, so the table never grows with the number of distinct keys you
have touched. `active_keys()` reports how many keys are held or waited on right now.

By default the per-key lock is not reentrant: a thread that re-enters a key it already
holds will deadlock. Pass `reentrant=True` to allow nesting on the same key within one
thread.

```python
locks = KeyedLock(reentrant=True)
with locks.lock("job-42"):
    with locks.lock("job-42"):  # same thread, same key: allowed
        ...
```

### Striped mode

When the key space is huge or unbounded and you would rather cap memory than track every
key, use `StripedLock`. It maps keys onto a fixed pool of locks: memory is allocated once
and never grows, at the cost of occasional false contention when two unrelated keys land
on the same stripe.

```python
from keyedlock import StripedLock

locks = StripedLock(stripes=256)
with locks.lock(user_id):
    ...
```

## Why

The "one lock per key" pattern is re-implemented constantly: a dict of locks guarded by a
meta-lock. Done naively the dict leaks, growing with every distinct key ever seen; done
carefully the reference counting is easy to get wrong under contention.

Existing options fall short. `mutexcache` creates a lock per key but keeps it forever, so
the table grows without bound. Per-key helpers like the one inside `fleche` are not
standalone packages. There is no small, typed, zero-dependency library that pairs
reference-counted cleanup with an optional striped mode. `keyedlock` is that: standard
library `threading` only, full type hints, `py.typed`, and `mypy --strict` clean.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
