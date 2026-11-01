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
- [ ] Mutation round (item 18)
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
Secret keys with failing `repr` and 1.2 MB values exercise bounded error paths.

## Remaining preparation

Wheel and sdist inspection, strict twine rendering and the actual 0.2.0 upgrade
passed in a clean venv (166 tests passed). Still run all available supported interpreters, the deliberate mutation round and final gates. No independent QA or
reviewer verdict is claimed by this preparation report.
