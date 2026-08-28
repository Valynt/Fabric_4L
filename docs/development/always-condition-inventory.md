# `always()` / `failure()` Condition Inventory — `pr-checks.yml`

> **Status: audit complete — zero executable overrides to constrain.**
>
> This inventory is the canonical record for every `always()`, `failure()`,
> or custom result condition in `.github/workflows/pr-checks.yml` (recorded at
> commit `421b26812`, the `check-external-deps` wiring). Its purpose is to
> distinguish **aggregators/reporters** (which must keep `always()` so
> failures stay visible and evidence is preserved) from **executable** steps
> (where `always()` would run genuine downstream test/build work after a
> failed prerequisite).
>
> **Headline conclusion:** every occurrence below is an aggregator, artifact
> upload, diagnostics capture, evidence generator, or cleanup step. There are
> **zero** executable occurrences, so **no workflow condition is narrowed**.
> This matches the plan's instruction: record the conclusion, make no code
> change, do not invent conditions.

---

## 1. Method

`pr-checks.yml` was scanned at commit `421b26812` for every `always()`,
`failure()`, and other result-based condition, at both job level and step
level. Each occurrence was classified by its role:

| Role | Meaning | `always()` disposition |
|---|---|---|
| **Aggregator** | Summarizes fan-in jobs, performs no substantive testing | **Preserve** — must run unconditionally |
| **Reporting / diagnostics** | Artifact upload, failure log capture, evidence generation, summary build | **Preserve** — evidence must exist on both success and failure |
| **Cleanup / teardown** | Releases backend resources (compose down) | **Preserve** — must run regardless of test outcome |
| **Executable** | Runs genuine downstream test/build/scaffold work | **Constrain** — must not run after failed prerequisite |

No occurrence fell into the **executable** bucket.

---

## 2. Job-level `always()` — aggregators (preserve)

| Job | Line | Role | Disposition |
|---|---|---|---|
| `unified-readiness-gate` | 2923 | Final required aggregator; fail-closed arbiter over all gated checks | **Preserve** |
| `aggregate-01-repository-integrity` | 3096 | Aggregator (V1-CI-001 Stage 1 shadow) | **Preserve** |
| `aggregate-02-code-quality-and-tests` | 3120 | Aggregator (V1-CI-001 Stage 1 shadow) | **Preserve** |
| `aggregate-05-tenant-isolation-and-behavior` | 3160 | Aggregator (V1-CI-001 Stage 1 shadow) | **Preserve** |

All four run `scripts/ci/aggregate_gate.py` over `toJSON(needs)` and perform
no substantive validation themselves. `unified-readiness-gate` additionally
fails closed: any required check with result `failure`, `cancelled`, `skipped`
(without a proven-safe scope mapping), or any *unknown* result sets `failed=1`
and exits 1 (see the `CHECKS`/`SCOPES` loop and the `*` case at
lines 3048-3052).

---

## 3. Step-level `failure()` — diagnostics capture (preserve)

These steps intentionally run when their job fails so logs and evidence are
captured for triage. None of them execute downstream test or build work.

| Job | Line | Step | Position |
|---|---|---|---|
| `layer5-contract-shape-regression` | 1405 | Upload Layer 5 contract diff artifacts | Preserve |
| `frontend-checks` | 1726 | Upload build artifacts on failure | Preserve |
| `p0-e2e-gate` | 1839 | Capture Compose diagnostics | Preserve |
| `runtime-contract-checks` | 2178 | Capture runtime contract service diagnostics | Preserve |
| `integration-checks` | 2329 | Capture logs on failure | Preserve |
| `integration-checks` | 2344 | Upload logs on failure | Preserve |

---

## 4. Step-level `always()` — reporting / evidence / cleanup (preserve)

### Structural, governance, and readiness jobs

| Job | Line | Step | Position |
|---|---|---|---|
| `structural-preflight` | 438 | Build PR diff violation summary artifact | Preserve (reporting) |
| `structural-preflight` | 449 | Upload structural reports | Preserve |
| `production-readiness-gate` | 529 | Upload production-readiness artifacts | Preserve |
| `governance-docs-check` | 697 | Upload docs validation artifacts | Preserve |

### Layer check jobs (test-result uploads and evidence)

| Job | Line | Step | Position |
|---|---|---|---|
| `layer1-checks` | 838 | Upload Layer 3 Cypher scope audit | Preserve |
| `layer1-checks` | 846 | Upload Layer 3 query entrypoint matrix | Preserve |
| `layer1-checks` | 854 | Upload Layer 3 audited mutation violation report | Preserve |
| `layer1-checks` | 879 | Upload test results | Preserve |
| `layer2-checks` | 975 | Upload test results | Preserve |
| `layer3-checks` | 1083 | Upload Layer 3 contract drift report | Preserve |
| `layer3-checks` | 1107 | Collect Layer 3 Cypher + tenancy release evidence | Preserve (evidence copy) |
| `layer3-checks` | 1117 | Upload test results | Preserve |
| `layer3-checks` | 1128 | Upload Layer 3 tenancy evidence artifacts | Preserve |
| `layer4-checks` | 1197 | Upload test results | Preserve |
| `layer5-checks` | 1269 | Upload test results | Preserve |
| `layer6-checks` | 1462 | Upload test results | Preserve |

### Shared, frontend, behavior, and E2E jobs

| Job | Line | Step | Position |
|---|---|---|---|
| `shared-and-tests-checks` | 1530 | Assert shared-package suite collected tests | Preserve (fail-closed assertion, no test execution) |
| `shared-and-tests-checks` | 1551 | Upload shared-package test results | Preserve |
| `frontend-checks` | 1655 | Upload bundle report | Preserve |
| `frontend-checks` | 1670 | Upload test results | Preserve |
| `frontend-checks` | 1680 | Upload frontend test report artifact (release evidence) | Preserve |
| `behavior-tests` | 1771 | Upload behavior test results | Preserve |
| `p0-e2e-gate` | 1846 | Upload P0 E2E artifacts | Preserve |
| `p0-e2e-gate` | 1857 | Tear down deterministic E2E backend (compose down) | Preserve (cleanup — releases resources regardless of result) |

### Contract, integration, and remaining gates

| Job | Line | Step | Position |
|---|---|---|---|
| `contract-checks` | 2024 | Upload compatibility shim report | Preserve |
| `contract-checks` | 2032 | Upload test results | Preserve |
| `runtime-contract-checks` | 2184 | Upload runtime contract artifacts | Preserve |
| `schemathesis-checks` | 2263 | Upload Schemathesis results | Preserve |
| `integration-checks` | 2336 | Upload smoke report | Preserve |
| `billing-entitlements-regression` | 2380 | Generate launch-checklist evidence | Preserve (evidence, not test execution) |
| `billing-entitlements-regression` | 2388 | Upload billing regression evidence | Preserve |
| `docker-compose-config-contract` | 2442 | Upload Docker Compose config artifacts | Preserve |
| `tenant-isolation-gate` | 2759 | Upload tenant isolation evidence | Preserve |
| `critical-behaviors-gate` | 2817 | Save critical-behaviors evidence | Preserve |
| `critical-behaviors-gate` | 2830 | Upload critical-behaviors evidence | Preserve |
| `critical-behaviors-gate` | 2838 | Upload behavior readiness audit report | Preserve |

---

## 5. Custom result conditions in the gate script

The `unified-readiness-gate` script reads `needs.<job>.result` for every job in
its `needs` list (lines 2966-2986, `CHECKS` array) and the `SCOPES` map
(lines 2995-3008). This is the fail-closed arbiter, not a skip:

- `success` → green.
- `failure` → root failure.
- `cancelled` → failure (cascade).
- `skipped` → green **only** when the job has a scope mapping and
  `change-scope` proved it out of scope (`SCOPES[...] == "false"`); otherwise a
  skip is an unproven loss of coverage and fails the gate.
- any other / unknown value → failure (`*` case), covering "not executed" and
  "skipped unexpectedly" without a mapping.

`check-external-deps` (wired in commit `421b26812`) intentionally has **no**
scope mapping: a skipped or failed `check-external-deps` is always a gate
failure, so a required external dependency cannot be silently dropped.

---

## 6. Verification checklist for future edits

When adding or changing an `always()`/`failure()`/result condition:

1. Classify the step as aggregator, reporting, cleanup, or executable.
2. If **executable**, replace blanket `always()` with an explicit
   result-gated condition (`needs.<dep>.result == 'success'` etc.) — do not run
   downstream test/build work after a failed prerequisite.
3. If **aggregator/reporter/cleanup**, keep `always()` — do not remove it and
   hide failures.
4. If the step is a required check, ensure a scope mapping exists **or** verify
   the `unified-readiness-gate` fail-closed handling treats its skip/failure as
   a gate failure.
5. Re-run this inventory's line-number audit and note the new commit.