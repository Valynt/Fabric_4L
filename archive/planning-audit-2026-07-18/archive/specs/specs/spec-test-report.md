# Spec: Full Test Suite Execution & Coverage Report

## Status
Draft — pending user confirmation

---

## Problem Statement

Run the entire automated test suite for the Fabric_4L monorepo and produce a
human-readable report covering pass/fail/skip counts and per-layer code coverage.
The monorepo has two test stacks:

- **Python (pytest)** — root `tests/` suite (2,826 collected tests) plus
  per-service suites under `services/layerN/` (299 additional test files across
  7 services)
- **Frontend (Vitest)** — `apps/web/src/` (129 test files, ~1,426 tests)

Several collection errors exist in the root suite (11 files) due to missing
service-local modules on `sys.path`. Node 20 is installed but the project
requires Node ≥22 for the frontend suite.

---

## Requirements

1. Fix the 11 Python collection errors by adding the relevant service `src/`
   directories to `PYTHONPATH` before running the root suite.
2. Resolve the two remaining structural errors:
   - `tests/test_cross_tenant_hostile.py` — imports `TEST_ORG_ID` from
     `tests.conftest`, which does not export it; needs investigation.
   - `tests/test_model_registry_integration.py` — imports
     `layer2_extraction.integration.model_registry_client` which does not exist
     (the module was removed/renamed); document as a known broken test.
   - `tests/ci/test_check_no_nul_bytes.py` — f-string syntax error in the test
     file itself; document as a known broken test.
3. Run the full Python root suite (`tests/`) with no `-m` filter, collecting
   pass/fail/skip/error counts.
4. Run each per-service pytest suite separately from its own directory, using
   the `pythonpath` declared in each service's `pyproject.toml`.
5. Measure per-layer Python coverage using `--cov=src --cov-report=term-missing`
   for each service suite.
6. Upgrade Node to 22 (via nvm source + install) and run the frontend Vitest
   suite with `--coverage` to get v8 coverage output.
7. Aggregate all results into a single markdown report saved to
   `reports/TEST_REPORT_<date>.md` and print a summary to console.

---

## Acceptance Criteria

- [ ] All 2,826 root Python tests are attempted (not silently skipped due to
      collection errors where fixable).
- [ ] Collection errors that cannot be fixed without source changes are
      documented with their root cause.
- [ ] Report states: total tests, passed, failed, skipped, errors — for each
      suite (root + each service + frontend).
- [ ] Coverage report includes overall % and per-file breakdown for each layer.
- [ ] Any failing test is listed with its full error message.
- [ ] Infrastructure-gated tests (postgres, redis, neo4j) that skip are counted
      and noted as "skipped — no live infra".
- [ ] Report file written to `reports/TEST_REPORT_<YYYY-MM-DD>.md`.
- [ ] No source code is modified.
- [ ] No production dependencies are installed or upgraded.

---

## Implementation Steps

### Phase 1 — Environment setup (non-destructive)

1. **Install test dependencies** (already partially done; verify complete):
   ```bash
   pip3 install -r tests/requirements-test.txt
   ```

2. **Upgrade Node to 22** using nvm (already present at
   `/usr/local/share/nvm/nvm.sh`):
   ```bash
   source /usr/local/share/nvm/nvm.sh && nvm install 22 && nvm use 22
   ```

3. **Install frontend dependencies** with the correct pnpm version:
   ```bash
   corepack enable && corepack prepare pnpm@10.18.1 --activate
   pnpm --dir apps/web install --frozen-lockfile
   ```

### Phase 2 — Fix Python collection errors

4. **Identify fixable collection errors** — the 11 errors fall into three
   categories:
   - **PYTHONPATH gaps** (8 files): `tests/layer3/test_*.py` and
     `tests/security/test_neo4j_cross_tenant_write_isolation.py` import from
     `api.dependencies`, `api.dependencies_tenant`, `api.cache` — all of which
     exist under `services/layer3-knowledge/src/`. Fix by prepending
     `services/layer3-knowledge/src` to `PYTHONPATH` when running the root
     suite.
   - **Missing module** (1 file): `tests/test_model_registry_integration.py`
     imports `layer2_extraction.integration.model_registry_client` which does
     not exist. Document as a broken test; exclude with `--ignore`.
   - **Conftest import mismatch** (1 file): `tests/test_cross_tenant_hostile.py`
     imports `TEST_ORG_ID` from `tests.conftest` which does not define it.
     Document as a broken test; exclude with `--ignore`.
   - **Syntax error** (1 file): `tests/ci/test_check_no_nul_bytes.py` has an
     f-string backslash syntax error. Document; exclude with `--ignore`.

5. **Run root suite with PYTHONPATH fix**:
   ```bash
   PYTHONPATH=services/layer3-knowledge/src:services/layer2-extraction/src:$PYTHONPATH \
     python3 -m pytest tests/ \
       --ignore=tests/test_model_registry_integration.py \
       --ignore=tests/test_cross_tenant_hostile.py \
       --ignore=tests/ci/test_check_no_nul_bytes.py \
       --ignore=tests/quarantine \
       -v --tb=short \
       --junit-xml=artifacts/pytest-root.xml \
       2>&1 | tee artifacts/pytest-root.log
   ```

### Phase 3 — Per-service pytest suites with coverage

6. For each service (`layer1-ingestion`, `layer2-extraction`, `layer3-knowledge`,
   `layer4-agents`, `layer5-ground-truth`, `layer6-benchmarks`, `api`), run:
   ```bash
   cd services/<service>
   PYTHONPATH=src:../..:<shared-paths> \
     python3 -m pytest tests/ \
       --cov=src --cov-report=term-missing --cov-report=json:../../artifacts/coverage-<service>.json \
       -v --tb=short \
       --junit-xml=../../artifacts/pytest-<service>.xml \
       2>&1 | tee ../../artifacts/pytest-<service>.log
   ```
   Each service's `pythonpath` from `pyproject.toml` is used to set
   `PYTHONPATH` correctly.

### Phase 4 — Frontend Vitest suite with coverage

7. Run Vitest with v8 coverage:
   ```bash
   pnpm --dir apps/web run test:coverage 2>&1 | tee artifacts/vitest.log
   ```

### Phase 5 — Aggregate and write report

8. Parse all `.log` and `.json` artifacts to extract:
   - Per-suite: total / passed / failed / skipped / errors
   - Per-layer coverage: overall % + per-file breakdown
   - All failing test names + error messages

9. Write `reports/TEST_REPORT_<YYYY-MM-DD>.md` with:
   - Executive summary table (suite × pass/fail/skip/coverage)
   - Per-suite detail sections
   - Known broken tests section (the 3 excluded files)
   - Coverage tables per layer
   - Failing test details with error messages

10. Print the executive summary table to console.

---

## Known Constraints

- **No live infra**: PostgreSQL, Redis, Neo4j are not running. Tests marked
  `requires_postgres`, `requires_redis`, `requires_neo4j` will skip. These are
  counted and noted in the report.
- **No source changes**: The 3 broken test files (`test_model_registry_integration.py`,
  `test_cross_tenant_hostile.py`, `test_check_no_nul_bytes.py`) are excluded
  via `--ignore`, not fixed.
- **pnpm version**: The workspace requires pnpm 10.18.1; the installed version
  is 9.15.9. `corepack` will be used to activate the correct version.
- **Coverage scope**: Per-layer coverage targets each service's `src/` directory.
  The root `tests/` suite does not run with `--cov` to avoid double-counting.

---

## Deliverables

| Artifact | Location |
|---|---|
| Root pytest log | `artifacts/pytest-root.log` |
| Per-service pytest logs | `artifacts/pytest-<service>.log` |
| Per-service coverage JSON | `artifacts/coverage-<service>.json` |
| Vitest log | `artifacts/vitest.log` |
| Final markdown report | `reports/TEST_REPORT_<YYYY-MM-DD>.md` |
| Console summary | stdout |
