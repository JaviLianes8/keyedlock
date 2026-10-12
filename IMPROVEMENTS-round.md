# keyedlock improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [ ] Interrupted acquisitions never leak a table entry
- [ ] Timeouts on every lock, `TimeoutError` when they expire
- [ ] Re-entry on a non-reentrant key or stripe raises instead of deadlocking
- [ ] `lock_many`: several keys in a fixed order, no lock-order deadlocks
- [ ] `AsyncKeyedLock`: asyncio variant, fair, cancellation safe
- [ ] Contracts: stress tests, typing, README examples, installed wheel e2e
- [ ] Docs: README, CHANGELOG, docstrings, packaging metadata
- [ ] Gates: ruff format, ruff check, mypy --strict, pytest
- [ ] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` gives `KeyedLock` (one lock per key, dropped when idle) and `StripedLock` (a
fixed pool). Reading it against the standard library documentation and real use:

- `lock()` counts the caller in before it calls `acquire()`. If the wait is interrupted
  (Ctrl+C lands in `acquire()`, which the docs say can happen on POSIX and, since 3.14, on
  Windows), the count is never given back: the key stays in the table forever and
  `active_keys()` never returns to zero.
- There is no way to wait with a limit. A stuck holder blocks every caller of that key
  for ever, and a request handler cannot give up after a budget.
- Re-entering a key on the same thread deadlocks silently. With `StripedLock` it is
  worse: two *different* keys that share a stripe deadlock when nested, and whether they
  share one depends on string hash randomisation, so it fails on some runs only.
- Locking two keys (a transfer between two accounts) has no safe helper: two threads
  taking the same pair in opposite order deadlock.
- Nothing for `asyncio`, where the same per-key pattern is just as common and
  cancellation is the normal way to give up.
- Tests cover the happy path with a few threads; nothing proves exclusion and cleanup
  under heavy contention, timeouts, exceptions and cancellation at the same time.

## Sources (fetched 2026-10-12)

- https://docs.python.org/3/library/threading.html
  (sha256 551db9a4e51cdbaf6246b942cf4bbb7c6ff642ac1b54285c8a646ccf9ad0e6b7).
  Lock objects: "which one of the waiting threads proceeds is not defined" (no fairness);
  `acquire(blocking=True, timeout=-1)`, "A timeout argument of -1 specifies an unbounded
  wait"; acquisition "can now be interrupted by signals on Windows" (3.14);
  `TIMEOUT_MAX`; RLock "must be released by the thread that acquired it".
- https://docs.python.org/3/library/asyncio-sync.html
  (sha256 9dc19545aa34713f11d9867e5ca1c88b321db7f044d8b8dbfcdb65262e78b9ae).
  `asyncio.Lock`: "Not thread-safe"; "Acquiring a lock is fair: the coroutine that
  proceeds will be the first coroutine that started waiting on the lock."

## Ranked improvements

1. **No leaks on interruption.** Any exception raised while waiting (including
   `KeyboardInterrupt` and asyncio cancellation) gives the reference back, so the table
   empties whenever the keys go idle. Proven by a primitive that raises inside `acquire`.
2. **Timeouts.** `lock(key, timeout=...)` on every lock. `None` waits forever, `0` tries
   once, a positive number waits at most that long; on expiry `TimeoutError` is raised
   and nothing is left in the table. Negative or NaN values raise `ValueError` before
   anything is touched; values above `threading.TIMEOUT_MAX` wait without limit.
3. **Re-entry fails fast.** With the default non-reentrant locks, a thread (or task)
   that tries to take a key, or a stripe, it already holds gets `RuntimeError` instead of
   a silent deadlock. `reentrant=True` keeps the old nesting behaviour.
4. **`lock_many(keys)`.** Takes several keys in one sorted order (stripes in index
   order for `StripedLock`), deduplicated, under one shared timeout, and releases
   everything already taken if a later key fails. Rejects a bare `str` passed as keys.
5. **`AsyncKeyedLock`.** Same contract on top of `asyncio.Lock`: fair per key,
   cancellation never leaks the table or the lock, timeouts never leave an orphaned
   acquisition holding the lock.
6. **Stress contracts.** Dozens of threads over a handful of keys with mixed timeouts
   and exceptions: at most one holder per key at any instant, every successful entry
   counted, distinct keys observed running concurrently, table empty at the end. Same
   for the asyncio variant with random cancellation.
7. **Fairness, documented.** The threaded locks inherit the undefined wake-up order of
   `threading.Lock`; the asyncio lock is first come, first served. Stated in the README.
8. **Typed public API, proven.** mypy reveals the documented types and rejects wrong
   arguments (`timeout="1"`, `stripes="4"`).
9. **Docs and packaging.** Every README example runs in the suite, API table complete,
   CHANGELOG with behaviour changes, version 0.2.0, installed-wheel e2e test.

## Out of scope

- A strictly fair (FIFO) mode for the threaded locks: it needs a hand-off queue per key
  with timeout races of its own. The standard lock is not fair either, and starvation
  needs sustained saturation of a single key.
- Bare `acquire(key)` / `release(key)` methods: the context managers pair them by
  construction, which is what keeps the reference count correct.
- Fork safety (`os.register_at_fork`): a child process should build its own locks.
