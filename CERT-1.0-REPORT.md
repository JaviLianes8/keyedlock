# keyedlock 1.0.0 certification report

Preparation date: 2026-11-01. Resumed source: `5addc52`.
The original preparation scorecard and evidence below are historical at `dbc21ba`.
Current correction results are in the QA round 5 section; the handoff below records
which independent verdicts still apply. Runtime code has not changed since `88c091b`.
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

## Preparation handoff

Items 1 to 15 and 18 are complete. The resumed checkout was clean and matched the
pushed release branch. All earlier commits and scratch evidence are retained.
The latest complete suite has 826 cases; round 5 records the eight-build interpreter
matrix and the mutation replays. No completed matrix or mutation round was repeated
for this documentation-only handoff.

On 2026-11-01, the PyPI JSON endpoint again returned HTTP 200 with 0.2.0 as its only
release. All three pinned Python specification files were fetched again and matched
the manifest hashes. Runtime file hashes match the saved round 5 restoration record.
Every Python source file is at most 200 lines. The README retains the exact
certification badge and link from the reference README.

The final handoff gates each exited zero independently: format (51 files), lint,
strict source typing (nine files), strict source-and-test typing (44 files), and
pytest (826 passed, no skips, 60.90 seconds) with fetched specifications, wheel e2e
and the actual PyPI 0.2.0 upgrade enabled. The suite exercises standard-library
oracles, seeded properties, docstrings, Markdown examples, archive inspection and
strict twine checks. Command evidence is retained in
`scratch/keyedlock-cert/resume-preparation/`. There is no CLI to exercise.

The rebuilt wheel contains 14 entries; the sdist contains 54. Both include LICENSE
and `py.typed`, and neither contains caches, scratch files or fetched specification
text. The sdist intentionally includes the contract suite and provenance manifest.
SHA-256:

- Wheel: `0a73606269254643c42c0a41d710cc080ea26cc7d8272ec9fba7505ab767b764`
- Sdist: `d21c625eb24b4b331e0b4c9ca038f87c686ee1e646fd16ddc473811c8308fb51`

### Inherited independent verdicts

| Lens | Last verdict | Reviewed commit | Applicability at handoff |
| --- | --- | --- | --- |
| a. API and docs | PASS, round 2 | `d58d87c` | Re-verification required: later timeout error handling and documentation changed. |
| b. Correctness and ground truth | PASS, round 1 | `b4ac8c9` | Re-verification required: later key validation, tables and timeout handling changed. |
| c. Adversarial and robustness | PASS, round 3 | `e21c990` | Retained: no runtime code changed after this review; later commits add contracts and clarify existing behavior. |
| d. Packaging and real e2e | PASS, round 1 | `b4ac8c9` | Re-verification required: later runtime, tests and documentation changed the artifacts. |
| e. Contract strength | FAIL, round 5 | `08c5d6d` | E-27 through E-31 have regression contracts and successful mutation replays in `dfafc71`; independent re-verification remains pending. |

The individual verdicts are recorded in the corresponding `lens-*/REPORT.md`
files under the scratch directory. No independent reviewer PASS exists for the
current release. Item 16, completion of item 19, merging and publication remain
separate stages. PR #3 remains open from `release/1.0.0` to `main`.

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

## QA findings, round 1

Date: 2026-11-01. Reviewed base: `b4ac8c90f7126726fd896fe2898c4dd83b4feb29`.
Correction commit: `4cf7b094743bff456d7f82514c5c8f0c4ccc91f8`
(`fix qa round one validation and contracts`).
All 13 supplied findings are addressed; independent lens re-verification remains
pending. No finding is disputed. Public names, signatures and defaults are retained.
Every behavior change is listed in CHANGELOG and the error/limit policy is in GUIDE.

| Finding | Change | Contract/evidence |
| --- | --- | --- |
| A1 | Validate actual hashing; normalize built-in unhashability, including nested members and writable memoryviews. | `test_protocol_errors.py`: all six entry points, safe complete tracebacks and valid read-only memoryview control. |
| A2 | Suppress displayed ordering-error causes and contexts. | Complete formatted traceback assertions for both keyed group methods. |
| A3 | Document normalization of comparison `TypeError`s, including subclasses, without a displayed chain. Other comparison exceptions retain propagation. | GUIDE policy corrected; explicit custom comparison exception contracts. This uses the finding's permitted documentation remedy. |
| C-001 | Bound each full-hash bucket to 64 unequal keys in group deduplication and active tables. Reject the 65th with fixed `ValueError`; remove entries by identity. | `test_key_limits.py`: groups, successive individual entries, equality-work bound, cleanup, exact capacity, equal-key reuse and stripe control. |
| C-002 | Normalize malformed collections and built-in key failures without exposing type names or displayed chains. | `test_protocol_errors.py` and the original A/C repro checks. |
| C-003 | Convert built-in memoryview hash rejection to the documented `TypeError`. | Direct and nested memoryviews across all six entry points. |
| C-004 | Validate underlying integers, normalized floats and rational numerator/denominator values before acquisition. | `test_numeric_validation.py`: negative integer/float subclasses, empty groups and negative rational underflow. |
| C-005 | Normalize integer stripe subclasses before range validation and allocation. | Negative and zero counts rejected; valid underlying count retained despite overridden conversion. |
| C-006 | Inspect built-in tuple/frozenset structure iteratively before hashing: at most 64 nested levels and 10,000 visited values. | All six 50,000-level tuple subprocess probes reject safely; exact depth boundary and shared-structure work limit tested. |
| E-01 | Add a deterministic striped group deadline contract with two acquisition delays. | M19 killed; second acquisition receives 0.25 seconds after the first spends 0.75 of a one-second budget. |
| E-02 | Test contended huge-timeout handoff on single and group methods across all classes. | M39 killed by 18 cases: infinity, twice the platform maximum and a 401-digit integer. |
| E-03 | Assert striped group body-exception identity, propagation and immediate reuse. | M49 killed by `test_group_body_exception_identity_and_cleanup`. |
| E-04 | Assert async group body-exception identity, propagation, zero active keys and immediate reuse. | M50 killed by `test_async_group_body_exception_identity_and_cleanup`. |

The first new contract run against the reviewed source produced 54 failures and
30 passes before implementation changes. The final suite adds 95 cases. Six deep
tuple probes failed by subprocess termination before the fix and now return a
documented `ValueError` without terminating the interpreter.

Collision measurements use ordinary integers `i * sys.hash_info.modulus`, three
samples per size. Group rejection, including cleanup, has the following medians:

| Keys supplied | Keyed seconds | Async seconds | Striped seconds (accepted) |
| --- | --- | --- | --- |
| 1,000 | 0.000653 | 0.001700 | 0.002318 |
| 2,000 | 0.000700 | 0.001809 | 0.003976 |
| 4,000 | 0.000643 | 0.001072 | 0.008579 |
| 8,000 | 0.000233 | 0.000938 | 0.017337 |
| 16,000 | 0.000226 | 0.000977 | 0.035742 |

Equality counters record exactly 2,080 comparisons before rejection for 100, 200,
400 and 800 supplied keys, for both keyed classes and both groups and successive
single acquisitions. Every idle table is empty. The fixed bound replaces the
reviewed quadratic behavior; it does not bound arbitrary user method execution.

The four surviving mutations were replayed individually on an isolated copy.
The unchanged new group contracts pass before and after replay: 22 passed.
M19, M49 and M50 each cause one failure; M39 causes 18 failures. M39's replacement
was applied to the integer and float overflow branches introduced by this fix.
No mutation failed during collection.

Validation:

- `ruff format --check .`: exit 0, 44 files formatted.
- `ruff check .`: exit 0.
- `mypy --strict src`: exit 0, nine files; `mypy --strict src tests`: exit 0, 37 files.
- Full pytest with a 300-second per-test limit, wheel installation, actual PyPI
  0.2.0 upgrade, archive checks and fetched-specification checks: 271 passed,
  no skips, exit 0 on CPython 3.14.6.
- Available interpreter matrix: CPython 3.10.22, 3.11.11, 3.11.18, 3.12.16,
  3.13.18, 3.14.6, 3.14.10 and 3.14.10 free-threaded. Each ran the revised source
  suite: 270 passed, one separately exercised wheel test skipped, exit 0.
  The free-threaded run verified the GIL was disabled.
- Original A/C targeted repro checks against the corrected source: 58 passed.
  The two A3 assertions requiring preservation of comparison `TypeError`s were
  deselected because the accepted remedy explicitly documents normalization;
  replacement contracts test that policy and its complete displayed traceback.

Detailed logs, isolated mutation edits, comparison counts and subprocess evidence
are retained under `scratch/keyedlock-cert/fix-r1/`. No new QA lens PASS is claimed;
the independent re-review, merge and publication remain separate stages.

## QA findings, round 2

Date: 2026-11-01. Reviewed base: `d58d87c6f764a02c796079a7ad54f96fec85b569`.
Correction commit: `88c091b82c98234c554beb3908498282f19c809d`
(`fix timeout conversion errors and strengthen acquisition contracts`).
All 13 supplied findings are addressed. No finding is disputed. Independent lens
re-verification remains pending. Public names, signatures and defaults are retained.

C-007 changes runtime behavior: malformed built-in float and rational component
conversions now raise a fixed `TypeError` without displaying the original chain.
Explicit failures from Python conversion methods/properties retain their identity
and message. CHANGELOG records this change and GUIDE documents the error policy.
E-05 through E-16 add missing regression contracts for existing behavior.

| Finding | Change | Contract/evidence |
| --- | --- | --- |
| C-007 | Normalize built-in numeric conversion failures without exposing caller-controlled type names. | `test_timeout_protocols.py`: 30 malformed conversion cases across all six methods, complete tracebacks, and 48 explicit-exception preservation cases. |
| E-05 | Accept exactly 10,000 visited values. | `test_structure_contracts.py::test_visited_value_boundary`: tuple, frozenset, mixed structure and subclasses, all six methods. |
| E-06 | Reject exactly 10,001 visited values with the fixed structure-limit error. | The same boundary contract checks rejection, cleanup and immediate reuse. |
| E-07 | Enforce frozenset and mixed tuple/frozenset nesting and structure limits. | `test_stored_nesting_boundary` checks 64 accepted levels and 65 rejected levels; visited-value boundaries also cover frozensets. |
| E-08 | Inspect stored tuple/frozenset subclass members despite overridden empty iteration. | Both structure contracts cover hidden-member subclasses across all six methods. |
| E-09 | Preserve explicit iterator `TypeError` identity and message. | `test_collection_contracts.py::test_iterator_typeerror_preserves_identity_and_message`: both `__iter__` and `__next__`, all three group methods. |
| E-10 | Accept bytearray collections as integer keys. | `test_bytearray_collection_acquires_integer_keys`: all group methods, duplicate keys, active counts and reuse. |
| E-11 | Deduplicate identical non-reflexive keys. | `test_identical_nan_keys_deduplicate_and_release`: both keyed classes hold one entry, release to zero and reacquire the identical NaN. |
| E-12 | Use the underlying positive integer despite a zero-valued float override. | `test_timeout_budgets.py` checks all six acquisition budgets; `test_group_contracts.py` checks threaded and async contended handoff. |
| E-13 | Retain non-integral Fraction magnitudes. | Acquisition recorders observe 0.5 and 1.5 seconds through all six methods with a controlled clock. |
| E-14 | Treat overflowing positive Fractions as unlimited. | `Fraction(10**400)` reaches acquisition as `None` and succeeds in contended single/group handoff for every class. |
| E-15 | Keep `TIMEOUT_MAX` finite and normalize larger values to unlimited. | All six methods check the float/integer maximum and the next representable float/next integer above it. |
| E-16 | Propagate comparison `ValueError` identity and message. | Both keyed group methods exercise failures during sorting and adjacent-order validation, then verify cleanup and reuse. |

Before the runtime fix, the new C-007 contracts produced **30 failures and 48
passes** against the reviewed source. After the fix all 78 pass. The complete
focused contract set passes before and after mutation replay: **295 passed**.
The full suite adds 273 cases to the reviewed baseline.

Each reported surviving mutation was applied alone to an isolated scratch copy,
with exact source restoration in `finally`. All twelve are now killed by actual
contract failures; none fails during collection. The N24 patch's indentation was
adjusted to match the surrounding conversion guard; its behavior is unchanged.

| Mutation | Regression | Failing cases | Catching contract |
| --- | --- | --- | --- |
| N01 | Reject 10,000 visits | 30 | `test_visited_value_boundary` |
| N02 | Accept 10,001 visits | 30 | `test_visited_value_boundary` |
| N05 | Skip frozenset inspection | 36 | Both structure boundary contracts |
| N06 | Trust overridden container iteration | 24 | Both structure boundary contracts |
| N10 | Replace explicit iterator `TypeError` | 3 | Iterator exception identity |
| N12 | Reject bytearray collections | 3 | Bytearray group acquisition |
| N15 | Remove key identity matching | 2 | Identical NaN deduplication |
| N21 | Use integer subclass float override | 12 | Acquisition budgets and threaded/async handoff |
| N22 | Invert Fraction magnitude | 18 | Numeric acquisition budgets |
| N24 | Raise on huge Fraction overflow | 12 | Acquisition budgets and threaded/async handoff |
| N26 | Make `TIMEOUT_MAX` unlimited | 12 | Numeric acquisition budgets |
| N30 | Rewrite comparison `ValueError` | 4 | Comparison exception identity |

Validation:

- `ruff format --check .`: exit 0, 50 files formatted.
- `ruff check .`: exit 0.
- `mypy --strict src`: exit 0, nine files; `mypy --strict src tests`: exit 0, 43 files.
- Full pytest with a 300-second per-test limit, wheel installation, actual PyPI
  0.2.0 upgrade, archive checks and fetched-specification checks: **544 passed**,
  no skips, exit 0 on CPython 3.14.6.
- Available interpreter matrix: CPython 3.10.22, 3.11.11, 3.11.18, 3.12.16,
  3.13.18, 3.14.6, 3.14.10 and 3.14.10 free-threaded. Each ran the revised source
  suite: **543 passed**, one separately exercised wheel test skipped, exit 0.
  The free-threaded run verified the GIL remained disabled through suite completion.
- Original lens C numeric/protocol probes against the corrected source, including
  both C-007 reproductions: **14 passed**, exit 0.

Detailed logs, mutation patches, commands and results are retained under
`scratch/keyedlock-cert/fix-r2/`. No new independent QA lens PASS is claimed;
re-review, merge and publication remain separate stages.

## QA findings, round 3

Date: 2026-11-01. Reviewed base: `e21c990a3d9f2c81892b5e7719f4aaa198f8e791`.
Correction commit: `b9dba092d70fa13232d5f78dc47c56f32bdb9a1c`
(`strengthen rational timeout contracts`).
All six supplied findings E-17 through E-22 are addressed. No finding is disputed.
These findings concern missing contracts: the existing runtime behavior is retained,
as are public names, signatures and defaults. GUIDE makes the rational component,
sign and zero-timeout policies explicit; CHANGELOG records the added coverage.
Independent lens re-verification remains pending.

| Finding | Change | Contract/evidence |
| --- | --- | --- |
| E-17 | Reject float, string and `__int__`-only numerators with the fixed `TypeError`. | `test_rational_components_require_index_protocol`: all six methods, suppressed error context, validation before key hashing and immediate reuse. |
| E-18 | Apply the same rejection contract to malformed denominators. | The same component contract exercises all three malformed kinds across all six methods. |
| E-19 | Preserve positive ratios represented by two negative components. | `test_numeric_timeout_budget_reaches_acquisition`: `(-1)/(-2)` reaches every acquisition as 0.5 seconds. |
| E-20 | Accept `Fraction(0, 1)` as an immediate attempt on every method. | Free-key success, exact zero acquisition budgets and held-key `TimeoutError`, with group rollback and cleanup. Threaded attempts finish while the holder still owns its key; async attempts finish without suspending for acquisition. |
| E-21 | Raise the fixed `ValueError` for zero denominators before acquisition. | `test_zero_denominator_raises_valueerror_before_acquisition`: negative, zero and positive numerators, all six methods, no key hashing and immediate reuse. |
| E-22 | Convert denominator index objects and preserve their explicit exceptions. | All six methods accept a successful `__index__` result as a 0.5-second budget and preserve `TypeError`/`ValueError` identity and message. Successful numerator conversion is also covered. |

The focused suite passes on the unchanged implementation: **228 passed**. The full
suite adds **102 cases**. The reviewer's original public witnesses also pass:
**66 passed**. No runtime correction or change to the numeric subclass domain was
needed; failures below demonstrate the new contracts detecting deliberate regressions.

Each of the six reported surviving mutations was replayed alone on an isolated
scratch copy using the reviewer's exact replacement text. Every mutant fails through
the contracts, with no collection failures. Source bytes are restored in `finally`
and checked against the shared repository. After replay, **228 focused tests pass**.

| Mutation | Regression | Failing cases | Catching contract |
| --- | --- | --- | --- |
| S07 | Coerce the numerator with `int` | 18 | Rational component index requirement |
| S08 | Coerce the denominator with `int` | 18 | Rational component index requirement |
| S09 | Reject either negative component | 6 | Two-negative-component acquisition budget |
| S10 | Reject zero rational numerators | 18 | Zero Fraction free/held acquisition and zero budget |
| S11 | Omit zero-denominator validation | 12 | Fixed `ValueError` before acquisition |
| S16 | Omit denominator index conversion | 24 | Malformed component rejection, successful index budget and explicit exception identity |

Validation:

- `ruff format --check .`: exit 0, 51 files formatted.
- `ruff check .`: exit 0.
- `mypy --strict src`: exit 0, nine files; `mypy --strict src tests`: exit 0, 44 files.
- Full pytest with a 300-second per-test limit, wheel installation, actual PyPI
  0.2.0 upgrade, archive checks and fetched-specification checks: **646 passed**,
  no skips, exit 0 on CPython 3.14.6.
- Available interpreter matrix: CPython 3.10.22, 3.11.11, 3.11.18, 3.12.16,
  3.13.18, 3.14.6, 3.14.10 and 3.14.10 free-threaded. Each ran the revised source
  suite: **645 passed**, one separately exercised wheel test skipped, exit 0.
  The free-threaded run verified the GIL remained disabled through suite completion.

Detailed logs, exact mutation patches, commands and restoration evidence are retained
under `scratch/keyedlock-cert/fix-r3/`. No new independent QA lens PASS is claimed;
re-review, merge and publication remain separate stages.

## QA findings, round 4

Date: 2026-11-01. Reviewed base: `b5603b43fa68901cf8f463c714c0692d6df3f7dd`.
Correction commit: `a50b764e24df37219c4a9b3a126942c56353c245`
(`strengthen rational budget and conversion contracts`).
All four supplied findings E-23 through E-26 are addressed. No finding is disputed.
These are missing regression contracts for existing behavior; no runtime change or
public API change was needed. GUIDE clarifies component-based rational conversion,
finite ratios with huge components and zero numerators with negative denominators.
CHANGELOG records the added coverage. Independent lens re-verification is pending.

| Finding | Change | Contract/evidence |
| --- | --- | --- |
| E-23 | Preserve the finite ratio of individually overflowing rational components. | `test_numeric_timeout_budget_reaches_acquisition`: irreducible `Fraction(10**400 + 1, 2 * 10**400 + 1)` supplies 0.5 seconds to all six methods. |
| E-24 | Accept zero numerators with a negative nonzero denominator. | All six methods check successful free-key acquisition, a zero acquisition budget and immediate `TimeoutError` on held keys, including group rollback and reuse. |
| E-25 | Reject negative rational values before float underflow can hide their sign. | `test_negative_denominator_underflow_raises_before_acquisition`: numerator 1 and denominator `-(10**400)` raise the fixed `ValueError` before key hashing on all six methods, followed by cleanup and reuse. |
| E-26 | Use the validated rational components regardless of `__float__`. | All six budget contracts cover overrides returning zero, a negative value, a different positive value, infinity and NaN. A zero-returning override also waits for threaded and async handoff on every method. |

The focused contracts pass on the unchanged implementation: **238 passed**. The
suite adds **66 cases**. The reviewer's original witnesses also pass: **26 passed**.
Each of the four reported mutations was replayed alone on an isolated scratch copy
using the reviewer's exact replacement text. All four cause contract failures;
none fails during collection. Source bytes are restored in `finally`, checked
against the shared repository and verified by SHA-256. After restoration the same
**238 focused tests pass**.

| Mutation | Regression | Failing cases | Catching contract |
| --- | --- | --- | --- |
| B02 | Convert huge components to float before division | 6 | Finite-ratio acquisition budgets |
| B03 | Reject zero with a negative denominator | 18 | Zero budgets and free/held acquisition |
| B04 | Miss negative ratios with positive numerators | 6 | Fixed `ValueError` before key hashing |
| B08 | Replace component division with `float(timeout)` | 36 | Five misleading float results and contended handoff |

Validation:

- `ruff format --check .`: exit 0, 51 files formatted.
- `ruff check .`: exit 0.
- `mypy --strict src`: exit 0, nine files; `mypy --strict src tests`: exit 0, 44 files.
- Full pytest with a 300-second per-test limit, wheel installation, actual PyPI
  0.2.0 upgrade, archive checks and fetched-specification checks: **712 passed**,
  no skips, exit 0 on CPython 3.14.6.
- Available interpreter matrix: CPython 3.10.22, 3.11.11, 3.11.18, 3.12.16,
  3.13.18, 3.14.6, 3.14.10 and 3.14.10 free-threaded. Each ran the revised source
  suite: **711 passed**, one separately exercised wheel test skipped, exit 0.
  The free-threaded run verified the GIL remained disabled through suite completion.

Detailed logs, exact mutation patches, commands and restoration evidence are retained
under `scratch/keyedlock-cert/fix-r4/`. No new independent QA lens PASS is claimed;
re-review, merge and publication remain separate stages.

## QA findings, round 5

Date: 2026-11-01. Reviewed base: `08c5d6dbe7b70a2726226cb4229e5e5391c97458`.
Correction commit: `dfafc71230fe38e4d77c18f0c32afa692a39600b`
(`strengthen rational timeout boundary contracts`).
All five supplied findings E-27 through E-31 are addressed. No finding is disputed.
The findings concern missing regression contracts for existing behavior. Runtime
code and the public API are unchanged. GUIDE clarifies component normalization
for direct and registered rational implementations and positive underflow;
CHANGELOG records the added coverage. Independent lens re-verification is pending.

| Finding | Change | Contract/evidence |
| --- | --- | --- |
| E-27 | Ignore overloaded comparisons when normalizing positive rational timeouts. | `test_numeric_timeout_budget_reaches_acquisition`: each of the six comparison operators returns a forced true or false result; all six methods still acquire with a 0.5-second budget. |
| E-28 | Keep a rational timeout equal to the platform maximum finite. | `Fraction(int(threading.TIMEOUT_MAX), 1)` reaches all six acquisition boundaries as `threading.TIMEOUT_MAX`, never `None`. |
| E-29 | Accept positive rational underflow as an immediate attempt. | `Fraction(1, 10**400)` produces zero budgets, succeeds on free keys and raises `TimeoutError` on held keys across all six methods; group rollback, idle cleanup and reuse are checked. |
| E-30 | Treat representable rational values above the platform maximum as unlimited. | `Fraction(2 * int(threading.TIMEOUT_MAX), 1)` reaches all six methods as `None`, covering the finite-conversion path separately from overflow. |
| E-31 | Normalize components for non-Fraction Rational implementations. | Direct and registered rational types with components 1 and 2 and `__float__` returning zero deliver a 0.5-second budget through all six methods. The direct type implements every abstract operation by delegation to the same Fraction ratio. |

The focused contracts pass on the reviewed runtime: **312 passed**. The full suite
adds **114 cases**. The reviewer's original witnesses also pass: **38 passed**.
Each of the five reported mutations was replayed alone on an isolated scratch copy
using the reviewer's exact replacement text. All five cause contract failures;
none fails during collection. Source bytes are restored in `finally`, checked
against the shared repository and verified by SHA-256. After restoration the same
**312 focused tests pass**.

| Mutation | Regression | Failing cases | Catching contract |
| --- | --- | --- | --- |
| C02 | Reject rationals through overloaded comparison | 12 | Six positive Fraction comparison cases and six registered-rational acquisition budgets |
| C05 | Make the rational platform maximum unlimited | 6 | Exact-maximum rational acquisition budgets |
| C06 | Reject positive rational underflow | 18 | Zero budgets and free/held acquisition across all methods |
| C07 | Cap representable rationals above the maximum | 6 | Unlimited acquisition budgets after finite conversion |
| C09 | Recognize only Fraction as rational | 12 | Direct and registered Rational component-derived budgets |

Validation:

- `ruff format --check .`: exit 0, 51 files formatted.
- `ruff check .`: exit 0.
- `mypy --strict src`: exit 0, nine files; `mypy --strict src tests`: exit 0, 44 files.
- Full pytest with a 300-second per-test limit, wheel installation, actual PyPI
  0.2.0 upgrade, archive checks and fetched-specification checks: **826 passed**,
  no skips, exit 0 on CPython 3.14.6.
- Available interpreter matrix: CPython 3.10.22, 3.11.11, 3.11.18, 3.12.16,
  3.13.18, 3.14.6, 3.14.10 and 3.14.10 free-threaded. Each ran the revised source
  suite: **825 passed**, one separately exercised wheel test skipped, exit 0.
  The free-threaded run verified the GIL remained disabled through suite completion.

Detailed logs, exact mutation patches, commands and restoration evidence are retained
under `scratch/keyedlock-cert/fix-r5/`. No new independent QA lens PASS is claimed;
re-review, merge and publication remain separate stages.
