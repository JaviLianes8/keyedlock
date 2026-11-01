# keyedlock 1.0.0 certification report

Preparation date: 2026-11-01. Validated source: `dbc21ba`.
Base: `main` at `4e54b50` (0.2.0). The interrupted branch's initial report at
`11e48ff` remains in history. `https://pypi.org/pypi/keyedlock/json` returned HTTP 200 on 2026-11-01:
0.2.0 was uploaded at 2026-11-01T02:11:21Z. Its earlier reported 404 is stale.

Progress:

- [x] Resume branch and establish baseline
- [x] Stable API, errors, typing and runnable docstrings (items 1 to 5)
- [x] Complete contracts, live ground truth and seeded properties (items 6, 7, 9)
- [x] Wheel consumers, real PyPI upgrade and interpreter matrix (items 8, 10)
- [x] README, GUIDE, CHANGELOG, metadata and archive inspection (items 11 to 14)
- [x] Four gates, each exiting zero independently (item 15)
- [x] Mutation round: 24 of 24 killed (item 18)
- [x] PR #3 and guard CLEAN
- [ ] Independent reviewer (item 16, separate stage)
- [ ] Merge and publish (item 17, separate stage)
- [ ] Five independent QA lenses (item 19, separate stage)

## Scorecard

| Item | Verdict | Evidence |
| --- | --- | --- |
| 1 | PASS | Same three classes, signatures and defaults; every change from PyPI 0.2.0 in CHANGELOG and upgrade contracts. |
| 2 | PASS | Exact `__all__` and package namespace contract; examples use public imports. |
| 3 | PASS | 34 doctest statements across all classes, public methods and the property; README/GUIDE examples execute. |
| 4 | PASS | `mypy --strict src tests`, 31 files; `py.typed` in both archives; installed consumer inference tests. |
| 5 | PASS | Built-in exception families documented; fixed messages, no key representations or unhashable type names. |
| 6 | PASS | 176 tests cover all public operations, ownership, FIFO, deadlines, rollback, cleanup, cancellation and errors. |
| 7 | PASS | Three Python spec files fetched live with provenance; real asyncio, RLock and dict differential output. |
| 8 | PASS | Clean wheel venv, external subprocess consumer, actual PyPI 0.2.0 upgrade; no CLI exists. |
| 9 | PASS | Seeded thread/task stress and key properties; queue/group scaling to 32,000, large secret/error inputs. |
| 10 | PASS | All eight distinct installed supported builds, including free-threaded 3.14.10 with GIL disabled. |
| 11 | PASS | Exact certification badge, verified standard-library comparison, absolute README links, strict twine checks. |
| 12 | PASS | Dated 1.0.0 section, 2026-11-01. |
| 13 | PASS | 1.0.0, Production/Stable, Python 3.10-3.14, MIT, keywords, project URLs, no runtime dependencies. |
| 14 | PASS | Wheel 12 entries, sdist 41; LICENSE and types present; no fetched text, caches, scratch or report files. |
| 15 | PASS | Format, lint, strict source types and pytest each exit zero separately; strict source/tests also passes. |
| 16 | pending | Independent reviewer is a separate stage; no inherited PASS. |
| 17 | ready | PR #3 from `release/1.0.0`; guard CLEAN; no merge or publication performed. |
| 18 | PASS | Final 24 single mutations all killed by contract tests; table below. |
| 19 | pending | All five independent lenses are a separate stage; no inherited PASS. |

## Baseline and API

At `11e48ff`, CPython 3.14.6: format, lint and strict source/tests types passed;
pytest: 124 passed, one opt-in wheel skip, 7.63 seconds.
The three exports and all constructor/method signatures and defaults are retained.
Changes from PyPI 0.2.0, each checked in the real upgrade and recorded in CHANGELOG:

- Timeout errors omit keys, never call `repr`, and identify a stripe for striped locks.
- Invalid option types and unhashable keys have fixed, bounded messages.
- `reentrant` rejects non-booleans instead of accepting truth values.
- Public class modules are `keyedlock`; old pickled class references still resolve.
- The incidental `annotations` package attribute is removed.
- Async queue removal uses an ordered mapping instead of linear scans on handoff
  and cancellation. FIFO and cancellation semantics are retained.

## Ground truth

Fetched live on 2026-11-01 from Python's v3.14.0 tag:

- https://raw.githubusercontent.com/python/cpython/v3.14.0/Doc/library/threading.rst
- https://raw.githubusercontent.com/python/cpython/v3.14.0/Doc/library/asyncio-sync.rst
- https://raw.githubusercontent.com/python/cpython/v3.14.0/Doc/library/stdtypes.rst

`tests/upstream/MANIFEST.json` records URL, revision, byte size, SHA-256 and PSF license.
Copies remain in scratch, outside the repository and both archives. The committed
refetch script was run successfully; the provenance test verifies every byte and
skips cleanly when `KEYEDLOCK_UPSTREAM` is unset.

The fetched text establishes unspecified thread wake order, recursive ownership,
async FIFO, the event-loop restriction and dictionary equality semantics. The
timeout-above-platform-limit rule is explicitly library policy, not Python behavior.
`test_reference.py` executes real `asyncio.Lock`, `threading.RLock` and `dict`
oracles: three seeded 200-task cancellation/FIFO schedules, recursive-depth ownership
probes and 3,000 random key multisets. Cases are authored, not claimed upstream vectors.

## Robustness

Thread stress: 48 seeds, 150 rounds each, mixed keys/groups, timeouts and failed bodies.
Async stress: three seeds, 300 tasks each, timeouts, failed bodies and cancellation;
unexpected task exceptions fail the test. Cancellation is checked while queued,
during handoff, inside a held context and during partial group acquisition.
Error contracts include a failing key `repr`, 1.2 MB values and 60,000-character
class names. Unequal colliding keys stay independent; user hash failures propagate.

Scaling on CPython 3.14.6, three samples per size, median seconds:

| Shape | 2,000 | 8,000 | 32,000 |
| --- | --- | --- | --- |
| Async FIFO handoff | 0.220 | 0.921 | 1.796 |
| Async random cancellation | 0.094 | 0.404 | 2.075 |
| Descending key groups | 0.013 | 0.051 | 0.271 |
| Duplicate key groups | 0.004 | 0.017 | 0.050 |

No quadratic growth was observed in these shapes. Hashing/comparison cost remains
subject to Python dictionary behavior and caller-defined key operations, as documented.

## Mutation round (item 18)

The first 20 mutations were killed at `e9fc9f3`. At `dbc21ba` they were replayed
with four additional mutations covering hashability validation: all 24 killed.
Each bug was applied alone to a scratch copy and tested with the named public
contract and `pytest -x --timeout=300`. Bytecode was disabled, the source restored
in `finally`, and every failure was a test assertion/error, not a collection failure.
No surviving or equivalent mutations were excluded. The unmodified suite passes
before and after the round.

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
| M21 | `_timing.py` | wrong unhashable-key error family | killed | `test_key_contracts.py::test_unhashable_key_errors_are_bounded` |
| M22 | `_timing.py` | echo unhashable type names | killed | `test_key_contracts.py::test_unhashable_key_errors_are_bounded` |
| M23 | `_async.py` | bypass async hashability validation | killed | `test_key_contracts.py::test_async_unhashable_key_errors_are_bounded` |
| M24 | `_striped.py` | bypass striped hashability validation | killed | `test_key_contracts.py::test_unhashable_key_errors_are_bounded` |

## Packaging and real consumers

`python -m build` builds the sdist and then the wheel from that sdist.
The wheel contains package modules, `py.typed`, metadata and LICENSE. The sdist adds
tests, the provenance manifest, refetch script, README, GUIDE and CHANGELOG.
Both pass `twine check --strict`. No third-party specification text is shipped.

The consumer runs with `-I` from an empty directory in a clean venv, verifies the
installed path, metadata and typing marker, and exercises threaded exclusion,
timeouts, reentry, groups, stripes, async FIFO and idle cleanup. Actual PyPI 0.2.0
is installed and exercised, then upgraded in place to the wheel and exercised again.
Changed messages, validation, namespace and old pickled class references are checked.
There is no CLI: no console entry point or `__main__.py` exists.

Artifact SHA-256 at `dbc21ba`:

- Wheel: `328d2293c1270c7a8bbc8229b30e6dd8c388226fdf28a786be713c29752eeef7`
- Sdist: `6785cf9c000ce3a501cf516681cad67257fcc5b63a5bbce88732a1bc8ab81a51`

## Interpreter matrix

The launcher had 13 stale paths; a disk scan located the actual installations.
Identical build/version copies are represented once. Each distinct supported build
runs the sdist's suite against the installed final wheel, with `src` absent and
fetched specs present. Only the separately exercised build/upgrade test skips.
Free-threaded Python uses `PYTHON_GIL=0`, verified disabled at pytest completion.

| CPython | Final result |
| --- | --- |
| 3.10.22 | 175 passed, 1 skipped in 20.89s |
| 3.11.11 | 175 passed, 1 skipped in 18.98s |
| 3.11.18 | 175 passed, 1 skipped in 17.14s |
| 3.12.16 | 175 passed, 1 skipped in 19.34s |
| 3.13.18 | 175 passed, 1 skipped in 8.54s |
| 3.14.6 | 175 passed, 1 skipped in 7.38s |
| 3.14.10 | 175 passed, 1 skipped in 6.87s |
| 3.14.10t | 175 passed, 1 skipped in 6.70s |

No supported minor version available on this PC was omitted. Removed launcher
registrations are unavailable, not successful test runs.

## Gates and handoff

At `dbc21ba`, each command ran separately: `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests`, and `pytest` all exit zero.
Pytest with `KEYEDLOCK_E2E=1`, `KEYEDLOCK_E2E_PYPI=1` and fetched specifications:
176 passed, no skips. Per-test timeout: 300 seconds; all temporary paths in scratch.
PR: https://github.com/JaviLianes8/keyedlock/pull/3. Guard: CLEAN.
Independent reviewer and five QA lenses remain pending; no prior PASS is claimed.
Merge and publication remain separate stages.
