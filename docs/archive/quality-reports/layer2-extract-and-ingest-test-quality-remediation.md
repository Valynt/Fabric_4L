# Layer 2 Extract-and-Ingest Test Quality Remediation

This remediation run audited and refined the new Layer 2 pipeline orchestration tests to improve determinism and maintainability while preserving API-contract coverage.

## Scope
- Layer: `services/layer2-extraction`
- Files reviewed:
  - `services/layer2-extraction/tests/test_extract_and_ingest_pipeline.py`
  - `services/layer2-extraction/tests/test_extraction.py` (context only)
- Framework: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`

## Discovery Snapshot
- Test files in Layer 2: 2
  - `tests/test_extraction.py`
  - `tests/test_extract_and_ingest_pipeline.py`
- Coverage config present in `pyproject.toml`:
  - `pytest-cov` enabled in dev dependencies
  - `[tool.coverage.run]` configured with `source = ["src"]`

## Quality Audit (Focused File)

### File: `tests/test_extract_and_ingest_pipeline.py`
- Test count: 4 async API-level orchestration tests
- Helpers: local fake store, frozen clock, Layer3 client double, artifact/payload builders

| Principle | Score (1-5) | Notes |
|---|---:|---|
| Behavior-Focused | 5 | Asserts public API kickoff/status contract and retry outcomes |
| Clear/Readable | 4 | Good intent; compact helper section improves scanability |
| Focused | 5 | One orchestration behavior per test |
| Deterministic | 4 | Deterministic monkeypatching and controlled time; tightened in remediation |
| Isolated | 5 | Autouse state reset and fake persistence boundary |
| Meaningful | 5 | Covers critical Task 6 paths (kickoff, staged states, queued retry, recovery) |
| Maintainable | 4 | Local helper layer avoids duplication without global test framework |
| **Total** | **32/35** | Excellent |

## Issues Found
- **P2 (determinism/maintainability):** Test helper used deprecated `datetime.utcfromtimestamp()` calls in Python 3.13 warning path.
  - Impact: noisy warning output and reduced long-term maintainability.
  - Remediation: replaced with deterministic naive UTC conversion helper:
    - `_UNIX_EPOCH` constant
    - `naive_utc_from_timestamp(timestamp)` helper

## Changes Applied
- Updated `services/layer2-extraction/tests/test_extract_and_ingest_pipeline.py`:
  - Added `_UNIX_EPOCH` and `naive_utc_from_timestamp()`.
  - Replaced deprecated `real_datetime.utcfromtimestamp(...)` calls in:
    - `FrozenClock.datetime_class().utcfromtimestamp`
    - retry scheduling assertion in `test_l3_unavailable_queues_retry_and_persists`

## Validation
- Single module pass:
  - `pytest tests/test_extract_and_ingest_pipeline.py -q`
- Determinism check (5 consecutive runs):
  - `1..5 | ForEach-Object { pytest tests/test_extract_and_ingest_pipeline.py -q }`
- Result: all runs passed.

## Residual Risks / Follow-ups
- Existing deprecation warnings remain in production module paths (`FastAPI on_event`, `datetime.utcnow()` in app/models). These are outside the scope of test-only remediation but should be tracked for future cleanup.
