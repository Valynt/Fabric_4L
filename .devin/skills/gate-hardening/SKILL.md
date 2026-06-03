---
skill_id: gate-hardening
name: gate-hardening
version: 1.0.0
description: Build a machine-verifiable production release gate system using TDD. Use when a codebase needs ship/no-ship test gates for tenant isolation, state consistency, degraded dependencies, workflow smoke tests, agent provenance, or observability. Also use when auditing or replacing an existing gate framework that may have false-confidence patterns.
side_effects: write
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Production Gate Hardening

Turn production readiness from narrative confidence into machine verification. This skill codifies a proven 7-phase process for building a release gate system where `pytest` is the single source of truth and a non-zero exit code blocks the release.

**Governing principle**: If all tests pass, there must be less than a 1% chance the application is not working as intended. There should be no scenario where all tests pass but the platform is not production-ready.

## Process Overview

1. Purge false-confidence infrastructure
2. Audit the codebase for gate-relevant constructs
3. Write failing tests (TDD)
4. Implement remediations until tests pass
5. Wire gates into CI and Makefile
6. Validate the full suite
7. Deliver results

Follow these phases in order. Each phase must complete before the next begins.

## Phase 1: Purge False-Confidence Infrastructure

Before writing any tests, eliminate existing gate infrastructure that can produce false positives.

Read `references/anti-patterns.md` for the full catalog of patterns to detect.

**Scan for these patterns:**
```bash
# Simulated results
grep -rn '_simulate\|simulated\|fake_result' scripts/gates/ tests/

# File-existence checks masquerading as tests
grep -rn 'os.path.exists.*pass\|Path.*exists.*pass' scripts/gates/

# Empty-directory pass-through
grep -rn 'max(.*total.*10\|max(.*len.*10' scripts/gates/

# Timeout fallback to pass
grep -rn 'TimeoutExpired.*True\|timeout.*pass' scripts/gates/

# Runner abstraction layers
ls scripts/gates/plugins/ scripts/gates/policy/ 2>/dev/null
```

**Actions:**
- Delete all runner scripts, plugins, policy engines, evidence collectors, and signing infrastructure
- Archive standalone operational scripts (load tests, pen test configs) to `docs/runbooks/operational/`
- Delete any `Makefile.gates` or intermediate gate files
- Keep the CI workflow file — it will be rewritten in Phase 5

**Exit criterion**: No file in the repository can produce a passing gate result without running a real pytest test.

## Phase 2: Audit the Codebase

Map the codebase to identify what needs gate coverage. Focus on six domains.

Read `references/gate-domains.md` for the full list of what to scan in each domain.

**Security and tenant isolation audit:**
```bash
# Run the route auth scanner
python scripts/scan_route_auth.py <routes_dir>

# Run the RLS coverage scanner
python scripts/scan_rls_coverage.py <migrations_dir>
```

Copy `scripts/scan_route_auth.py` and `scripts/scan_rls_coverage.py` from this skill into the project's scripts directory for reuse.

**State consistency audit:**
- Extract backend enum/model values (Python AST or regex)
- Extract frontend type literals (TypeScript regex)
- Diff the two sets

**Remaining domains** (chaos, smoke, agent, observability):
- Identify external dependencies and their failure modes
- List core workflow types and their expected state transitions
- Check if agent output schemas exist as Pydantic models
- Check if audit/metrics emission code exists

**Output**: Write findings to a `codebase_findings.md` file with file paths, line numbers, severity (P0/P1/P2), and expected test initial state.

## Phase 3: Write Failing Tests (TDD)

Write tests that fail initially, proving they detect real issues. Tests that pass on first run against a known-broken codebase are suspect.

**Setup:**
1. Copy `templates/conftest_template.py` to `tests/conftest.py` and customize paths
2. Create test directories: `tests/security/`, `tests/state/`, `tests/config/`
3. Add additional directories as needed: `tests/chaos/`, `tests/smoke/`, `tests/evals/`, `tests/obs/`

**Implementation order** (highest risk reduction first):
1. `tests/security/test_tenant_context_contract.py` — route auth scanning
2. `tests/security/test_rls_enforcement.py` — migration RLS scanning
3. `tests/state/test_state_alignment.py` — frontend/backend enum sync
4. `tests/security/test_cross_tenant_api.py` — endpoint auth enforcement
5. `tests/security/test_export_tenant_access.py` — export namespace isolation
6. `tests/config/test_startup_tenant_validation.py` — boot-time security checks

**Test design rules:**
- Tests scan real source files (AST, regex, file reads) — not mock objects
- Tests fail when the vulnerability exists and pass when it is fixed
- Every test has a docstring explaining what invariant it enforces
- No test imports the application's runtime dependencies (FastAPI, SQLAlchemy) — gate tests are static analysis

**Run after writing each suite:**
```bash
python3 -m pytest tests/<domain>/ -v --tb=short --no-header -p no:randomly
```

Expect failures. Document each failure with the file, line, and root cause.

## Phase 4: Implement Remediations

For each failing test, implement the minimum code change to make it pass.

**Common remediations:**
- Replace `Depends(get_db)` with `Depends(get_db_from_context)` in route files
- Add `require_authenticated` dependency to unprotected endpoints
- Create Alembic migrations for missing RLS policies
- Fix inconsistent GUC variable names in RLS policies
- Add `FORCE ROW LEVEL SECURITY` to migration upgrade functions
- Prefix export S3 keys with `{tenant_id}/`
- Add startup validators for JWT secret strength, superuser detection
- Add missing enum values to frontend TypeScript types
- Remove duplicate enum aliases from backend models

**For intentionally unsafe endpoints** (pre-auth, webhooks):
- Add a `# SECURITY: intentional — <reason>` comment above the endpoint
- Add the filename to the test's allowlist

**Run the full suite after each remediation:**
```bash
python3 -m pytest tests/security/ tests/state/ tests/config/ -v --tb=short --no-header -p no:randomly
```

## Phase 5: Wire Gates into CI and Makefile

**Makefile targets:** Copy patterns from `templates/makefile_gates.mk` into the project Makefile. Each `gate-*` target is a direct `pytest` invocation. `gate-all` runs every domain.

**CI workflow:** Use `templates/ci_workflow.yml` as the starting point. Each gate domain is a separate CI job. The `ship-decision` job aggregates results.

**Key rules:**
- No step between `pytest` and the CI exit code
- No `continue-on-error: true` on gate jobs
- The `ship-decision` job uses `if: always()` to run even when gates fail
- Only enable gate jobs for domains that have real tests

## Phase 6: Validate the Full Suite

```bash
make gate-all
```

**Acceptance criteria:**
- All tests pass (exit code 0)
- No test is skipped (skips indicate missing dependencies)
- No test uses `pass` as its body (stub tests are false confidence)
- Total test count matches expected count from Phase 3

**If pre-existing broken tests are found:** quarantine them to `tests/<domain>/_quarantine/` with a `conftest.py` that blocks collection and a README explaining why.

## Phase 7: Deliver Results

Commit and provide a delivery summary: total tests (pass/fail), files changed, critical findings table, remaining work, and any manual steps needed.

## Resources

- **`scripts/scan_route_auth.py`** — Scan FastAPI route files for unsafe dependency patterns (RLS bypass, optional auth on writes, missing auth). Copy into the project.
- **`scripts/scan_rls_coverage.py`** — Scan Alembic migrations for RLS policy gaps (missing policies, unsafe NULL patterns, inconsistent GUC names). Copy into the project.
- **`references/gate-domains.md`** — Detailed test patterns and code examples for all six gate domains. Read during Phase 2 and Phase 3.
- **`references/anti-patterns.md`** — Catalog of false-confidence patterns to detect and eliminate. Read during Phase 1.
- **`templates/conftest_template.py`** — Root conftest.py with tenant fixtures. Copy to `tests/conftest.py` during Phase 3.
- **`templates/makefile_gates.mk`** — Makefile gate target patterns. Copy into project Makefile during Phase 5.
- **`templates/ci_workflow.yml`** — GitHub Actions workflow for pytest-direct gates. Copy to `.github/workflows/` during Phase 5.
