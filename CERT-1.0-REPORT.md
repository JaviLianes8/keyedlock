# keyedlock 1.0.0 certification report

Preparation date: 2026-11-01. Base: `main` at `4e54b50` (0.2.0).
The existing release branch's initial report at `11e48ff` was retained in history.
PyPI now serves 0.2.0: `https://pypi.org/pypi/keyedlock/json` returned HTTP 200
on 2026-11-01, with upload time 2026-11-01T02:11:21Z. The earlier 404 is stale.

Progress:
- [x] Resume `release/1.0.0`; baseline gates on 0.2.0
- [x] API, errors, typing, runnable docstrings (items 1 to 5)
- [x] Fetch real ground truth and compare standard-library output (item 7)
- [x] Expand contract and seeded stress tests (items 6, 9)
- [x] README, GUIDE, dated CHANGELOG and package metadata (items 11 to 13)
- [ ] Built wheel, PyPI upgrade, archives and interpreter matrix (items 8, 10, 14)
- [x] Mutation round (item 18): 20 of 20 killed
- [ ] Final gates (item 15)
- [ ] PR and guard
- [ ] Independent reviewer (item 16, separate stage)
- [ ] Merge and publish (item 17, separate stage)
- [ ] Five independent QA lenses (item 19, separate stage)

## Baseline

At 11e48ff, Python 3.14.6: format, lint and `mypy --strict src tests` exit 0;
pytest: 124 passed, 1 skipped (opt-in wheel test), 7.63 seconds.
There were no completed lens reports or reviewer verdicts to carry forward.

## API and compatibility

The three exports, constructor signatures, defaults and methods are retained.
All classes, public methods and the `stripes` property have executed doctest examples.
README and GUIDE code blocks run as tests and verify their printed output.
Errors retain built-in exception families, documented in GUIDE.

Changes from PyPI 0.2.0, each in CHANGELOG:
- Timeout messages omit keys and never call key representations. Striped timeouts
  identify the stripe. Invalid option types use fixed messages, omitting type names.
- Unhashable keys raise a fixed `TypeError` without exposing their type name.
- `reentrant` rejects non-booleans instead of accepting their truth values.
- The incidental `annotations` package attribute is removed.
- Public class modules are `keyedlock`; old pickled class references still resolve.
- Async queue deletion uses an ordered mapping, avoiding scans on every successful
  handoff or cancelled waiter. FIFO and cancellation semantics are retained.

## Ground truth

Fetched on 2026-11-01, Python's tagged v3.14.0 documentation:
- https://raw.githubusercontent.com/python/cpython/v3.14.0/Doc/library/threading.rst
- https://raw.githubusercontent.com/python/cpython/v3.14.0/Doc/library/asyncio-sync.rst
- https://raw.githubusercontent.com/python/cpython/v3.14.0/Doc/library/stdtypes.rst

`tests/upstream/MANIFEST.json` records revision, URL, size, SHA-256 and PSF license.
The documents remain outside the repository in the certification scratch directory.
`scripts/fetch_upstream.py` refetches and verifies them; the provenance test skips
when `KEYEDLOCK_UPSTREAM` is unset and checks every byte when it is set.

The fetched text establishes unspecified thread wake order, recursive ownership,
async FIFO, the event-loop restriction and dictionary equality rules. The library's
timeout-above-platform-limit policy is explicitly its own, not a Python spec claim.
`test_reference.py` executes real `asyncio.Lock`, `threading.RLock` and `dict`
oracles. Three seeds compare cancellation/FIFO traces (200 tasks each) and 3,000
random key multisets; recursive-depth probes verify ownership after inner release.
Schedules are authored test cases, not claimed to be upstream vectors.

## Robustness

Thread stress uses 48 seeds, 150 rounds per thread, mixed single/group acquisitions,
timeouts and failed bodies. Async stress uses three seeds with 300 tasks each,
mixed timeouts, failed bodies and cancellation. Results reject unexpected task errors.
Contracts exercise cancellation during handoff, while queued, while holding and
during partial group acquisition; cleanup is checked through the public API.
Secret keys with failing `repr`, 1.2 MB values and 60,000-character class names
exercise bounded error paths. Unequal keys with identical hashes remain independent.

## Mutation round (item 18)

At `e9fc9f3`, each bug was applied alone to a scratch copy, followed by a targeted
public contract test with `pytest -x --timeout=300`. Bytecode was disabled, the
original module was restored in `finally`, and each mutant exited 1 with an actual
test failure. All 20 were killed; no equivalent or surviving mutant was excluded.
The complete unmodified suite passed before the round and is repeated afterward.

| ID | Module | Mutation | Result | Contract that caught it |
| --- | --- | --- | --- | --- |
| M01 | `_keyed.py` | leak a checkout reference | killed | `test_keyed.py::test_table_empties_after_release` |
| M02 | `_keyed.py` | overcount active keys | killed | `test_keyed.py::test_table_empties_after_release` |
| M03 | `_striped.py` | accept zero stripes | killed | `test_striped.py::test_rejects_non_positive_stripe_count` |
| M04 | `_striped.py` | collapse all stripes | killed | `test_striped.py::test_keys_on_different_stripes_run_in_parallel` |
| M05 | `_timing.py` | reject zero timeout | killed | `test_timeouts.py::test_zero_timeout_succeeds_on_a_free_key` |
| M06 | `_timing.py` | accept boolean timeout | killed | `test_timeouts.py::test_non_numeric_timeouts_are_rejected` |
| M07 | `_timing.py` | drop platform overflow cap | killed | `test_timeouts.py::test_timeouts_beyond_the_platform_limit_wait_without_limit` |
| M08 | `_timing.py` | keep duplicate keys | killed | `test_lock_many.py::test_duplicates_are_taken_once` |
| M09 | `_timing.py` | accept partial orders | killed | `test_lock_many.py::test_keys_without_a_total_order_are_rejected` |
| M10 | `_timing.py` | stop spending the group deadline | killed | `test_lock_many.py::test_later_keys_get_only_what_is_left_of_the_budget` |
| M11 | `_primitive.py` | leave the primitive locked on release | killed | `test_striped.py::test_an_exception_in_the_body_releases_the_stripe` |
| M12 | `_timing.py` | raise the wrong timeout family | killed | `test_timeouts.py::test_zero_timeout_fails_at_once_on_a_held_key` |
| M13 | `_fifo.py` | serve async waiters in reverse order | killed | `test_async.py::test_waiters_are_served_first_come_first_served` |
| M14 | `_fifo.py` | let a zero-timeout newcomer enter a held key | killed | `test_async.py::test_timeouts_raise_and_leave_nothing_behind` |
| M15 | `_async.py` | retain idle async entries | killed | `test_async.py::test_same_key_serializes_and_cleans_up` |
| M16 | `_keyed.py` | format secret keys on timeout | killed | `test_safety.py::test_thread_timeout_never_formats_keys` |
| M17 | `_keyed.py` | accept non-boolean reentrant option | killed | `test_safety.py::test_reentrant_requires_a_bool` |
| M18 | `_primitive.py` | ignore recursive mode | killed | `test_reentry.py::test_keyed_reentrant_mode_allows_nesting` |
| M19 | `_fifo.py` | give ownership to an expired waiter | killed | `test_async.py::test_timeouts_raise_and_leave_nothing_behind` |
| M20 | `_async.py` | lose async owner tracking | killed | `test_async.py::test_reentry_by_the_same_task_raises` |

## Packaging and real consumers

Wheel and sdist are built with `python -m build`. The wheel contains package code,
`py.typed`, metadata and LICENSE. The source archive additionally contains tests,
the provenance manifest, the refetch script, README, GUIDE and CHANGELOG. No fetched
specification, cache, scratch file or certification report is shipped.
`twine check --strict` checks both archive descriptions.

The external consumer runs with `-I` from an empty directory in a clean venv and
checks the installed path, metadata, typing marker, threaded exclusion, timeout,
reentry, group locking, stripe collisions, async FIFO and idle cleanup. The upgrade
check installs actual PyPI 0.2.0, runs the same consumer, records pickled class
references, upgrades in place to the wheel, then reruns both common and changed
contracts. No CLI exists: there are no console entry points or `__main__.py`.

## Interpreter matrix

The Windows launcher listed 13 stale paths to removed interpreters. A disk scan
located the actual portable CPython installations; identical build/version copies
are represented once. Every distinct available supported build runs the source
archive's suite against the installed wheel with no `src` directory. The opt-in
build/upgrade test is exercised separately. Free-threaded runs force `PYTHON_GIL=0`
and verify it stays disabled through the end of pytest.

The first matrix passed all eight distinct builds (165 passed, one opt-in skip each).
A later bounded-error regression added ten tests; final wheel revalidation is pending.

## Independent stages

Items 16 and 19 are pending the independent reviewer and five fresh QA lenses.
No prior PASS verdicts exist. Item 17 merge and publication are left to the maintainer.
