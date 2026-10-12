# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

### Added

- `timeout` on every `lock`: `None` waits for ever, `0` tries once, a number of seconds
  waits at most that long, then `TimeoutError`. Negative or NaN values raise `ValueError`,
  values that are not real numbers `TypeError`; values above `threading.TIMEOUT_MAX`
  (huge integers included) mean no limit.
- `lock_many(keys, *, timeout=None)` on `KeyedLock` and `StripedLock`: takes several keys
  (or stripes) once each in one global order, so callers cannot deadlock each other, and
  releases what it took if a later key fails. Keys without a total order (sets, NaN,
  mixed types) and a bare `str` raise `TypeError`.
- `AsyncKeyedLock`: the asyncio counterpart, strictly first come, first served per key
  (timed waiters included), safe under cancellation and timeouts, with `lock`,
  `lock_many` and `active_keys`.

### Changed

- Re-entering a key (or, for `StripedLock`, a stripe) already held by the same thread
  raises `RuntimeError` instead of deadlocking, unless the lock is `reentrant=True`.
- `StripedLock` rejects a non-integer `stripes` with `TypeError`.

### Fixed

- An exception raised while waiting for a key (for example `KeyboardInterrupt`) no longer
  leaves the key in the table for ever, and neither does a key whose hash changed while
  it was held.

## [0.1.0]

- First release.
- `KeyedLock`: per-key locking with reference-counted table cleanup and an optional
  reentrant mode.
- `StripedLock`: a fixed pool of locks that caps memory for large or unbounded key spaces.
