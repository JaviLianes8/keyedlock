# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-01

### Stable

- `KeyedLock`, `StripedLock` and `AsyncKeyedLock`, their constructors, `lock`,
  `lock_many`, counts and built-in exception families are the stable public API.
- Python 3.10 through 3.14, with no runtime dependencies and shipped type information.

### Changed

- Timeout errors no longer include the key or call its `repr`. Striped timeout errors
  identify the stripe index instead. Invalid timeout and stripe types use fixed messages
  without the supplied type name. This keeps keys and huge inputs out of library errors.
- Unhashable keys raise `TypeError("key must be hashable")`, omitting their type name.
- Built-in hash rejection includes nested unhashable members and writable memoryviews.
  Invalid collections use a fixed `TypeError`; normalized errors suppress displayed
  exception chains that could reveal caller-controlled type names.
- Group comparison `TypeError`s, including user subclasses, use a fixed total-order
  `TypeError` without a displayed chain. This normalization policy is now explicit.
- Keyed groups and active tables reject more than 64 unequal keys sharing one hash
  with a fixed `ValueError`. Equal keys retain dictionary semantics; stripe collisions
  remain unrestricted. Cleanup removes entries by identity without rehashing keys.
- All classes reject tuple/frozenset keys exceeding 64 nested levels or 10,000 visited
  values with fixed `ValueError`s before recursive built-in hashing.
- Timeout validation checks normalized numeric values, preserving integer and rational
  signs before float conversion. Integer stripe subclasses use their underlying value,
  so overloaded comparisons cannot allow negative timeouts or empty stripe pools.
- `reentrant` must be a boolean; truthy and falsey non-booleans now raise `TypeError`.
- Public classes identify their module as `keyedlock` instead of a private module.
  Existing class references pickled through the old module paths still load.
- The incidental `annotations` module attribute is removed; only the documented
  classes remain as non-underscore package attributes.

### Fixed

- Malformed float conversions and rational numerator/denominator conversions now
  raise a fixed `TypeError` without displaying caller-controlled type names or the
  original exception chain. Explicit exceptions from Python conversion methods
  retain their identity and message.
- Async waiter handoff and cancellation remove queue entries in constant time instead
  of scanning the remaining queue. FIFO order and cancellation behavior are unchanged.

### Added

- Runnable examples for every public class, method and property, a detailed guide,
  standard-library differential tests and expanded error and contract coverage.
- Contracts for striped group deadlines, contended huge-timeout handoff, and striped
  and async group body-exception identity, propagation and cleanup.
- Exact tuple/frozenset structure boundaries, stored-member validation for subclasses,
  iterator/comparison exception identity, bytearray collections and identical NaN keys.
- Acquisition-budget contracts for integer subclasses, fractional seconds, enormous
  positive fractions and the platform timeout boundary, including contended handoff.
- Rational timeout contracts for component index conversion, malformed components,
  normalized signs, zero denominators and zero-valued fractions on free and held locks.
  The guide makes these existing behaviors explicit; runtime behavior is unchanged.
- Rational timeout contracts for finite ratios with huge components, zero numerators
  with negative denominators, negative ratios that underflow, and misleading
  `__float__` overrides, including contended acquisition on every method. These
  additions preserve the existing runtime behavior and public API.
- Rational timeout contracts for misleading comparisons, the exact platform maximum,
  representable values above it, positive underflow on free and held keys, and direct
  or registered `numbers.Rational` implementations with misleading float conversion.
  All six acquisition methods retain their existing behavior; the guide clarifies
  the component and positive-underflow policies.

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
