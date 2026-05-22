# Anti-Drift Hardening Deliverable

**Date:** 2026-05-12
**Scope:** Layer 3 focused, with repo-wide guardrail coverage for P0 drift categories
**Status:** Guardrails implemented, baselines created, and wired into CI. All P0 checks pass with `--strict --use-baseline`.

---

## Summary

Anti-drift hardening is complete for the implemented guardrail scope. These checks reduce regression risk and support production-readiness review, but full platform production readiness is not claimed unless all production gates pass with evidence.

---

## Guardrails Created

### 1. `scripts/ci/check_security_regressions.py` — NEW

Checks for:

- `debug_info` leaked in exception responses
- Infrastructure URIs in health-check JSON (`neo4j_uri` exposure)
- Fake health checks reporting `healthy` without actual I/O
- Redis `KEYS` in production code paths (requires `SCAN`)
- Broad `DeprecationWarning` suppression in pytest configs

**Result:**

```text
$ python scripts/ci/check_security_regressions.py --strict
Security regression findings: 0
PASS
```

### 2. `scripts/ci/check_deprecation_drift.py` — NEW

Checks for:

- `datetime.utcnow()` in source (Python 3.12 deprecation)
- Pydantic v1 APIs: `.parse_raw()`, `.parse_obj()`, `__root__`
- Invalid FastAPI response field types (`Request | None`)
- Broad deprecation warning suppression in pytest configs

**Result:**

```text
$ python scripts/ci/check_deprecation_drift.py --strict --use-baseline
Deprecation drift findings: 0
PASS
```

**Fixed:**

- `tests/layer3/test_typed_payloads.py`: replaced 2 `datetime.utcnow()` with `datetime.now(UTC)`
- `scripts/perf/analyze-connection-pools.py`: replaced 3 `datetime.utcnow()` with `datetime.now(UTC)`

**Baselined (30 entries):**

- `value_fabric/shared/rate_limiting/tenant_rate_limiter.py`: 3 `datetime.utcnow()` — shared production code; cross-layer testing required before migration
- `services/layer2-extraction/`: 7 `datetime.utcnow()` — Layer 2 production code; outside current scope
- `services/layer4-agents/`: 1 `datetime.utcnow()` + 5 `Request | None` — Layer 4 production code; outside current scope
- `services/layer4-agents/tests/`: 8 `datetime.utcnow()` — Layer 4 test code; outside current scope
- `tests/` (repo root): 6 `datetime.utcnow()` — repo-level test code; outside current scope

**Baseline file:** `docs/reference/deprecation-drift-baseline.json`

### 3. `scripts/ci/check_migration_safety.py` — NEW

Checks for:

- `print()` in migration scripts (requires structured logging)
- Destructive Cypher without `MIGRATION_REVIEW_REQUIRED` marker
- Neo4j Enterprise-only constraints without Community fallback note
- Missing `dry_run` parameter

**Result:**

```text
$ python scripts/ci/check_migration_safety.py --strict --use-baseline
Migration safety findings: 0
PASS
```

**Baselined (156 entries):**

- `services/layer2-extraction/`: missing `dry_run`, `print()` in migrations, destructive Cypher without markers, Enterprise-only constraints without fallback notes
- `services/layer4-agents/`: same categories as above
- All findings are pre-existing migration script debt outside Layer 3 hardening scope

**Baseline file:** `docs/reference/migration-safety-baseline.json`

### 4. `scripts/ci/check_readiness_language.py` — NEW

Checks for unqualified production-readiness claims in reports/docs/CI:

- "production ready", "GA ready", "fully complete", "enterprise ready", "launch ready", "all gates pass"

**Result:**

```text
$ python scripts/ci/check_readiness_language.py --strict --use-baseline
Readiness language findings: 0
PASS
```

**Fixed:**

- `scripts/ci/check_readiness_language.py`: added quote/backtick skip logic so documented/discussed phrases (e.g. in this deliverable's own "Checks for" list) no longer trigger false positives

**Baselined (9 entries):**

- `reports/repo-cleanup/BACKEND_TOPOLOGY_STATUS_2026-05-02.md`: historical report
- `reports/repo-cleanup/PYTEST_COLLECTION_REMEDIATION_REPORT_2026-05-02.md`: historical report (4 occurrences)
- `docs/comprehensive-platform-documentation.md`: legacy docs
- `docs/ValuePack_Framework_v2.0.md`: legacy docs
- `docs/archive/2026-04-27/ARCHIVED_MULTI_TENANCY_CONFIRMATION.md`: explicitly archived
- `docs/validation/backend_integrated/final_evidence_report.md`: historical validation report

**Baseline file:** `docs/reference/readiness-language-baseline.json`

---

## Guardrails Extended

### 5. `scripts/ci/check_deprecated_namespace_imports.py` — EXTENDED

Added `--check-shims` flag to detect service wrappers containing non-trivial domain logic (duplicate logic across `value_fabric/layer3/` and `services/layer3-knowledge/src/`).

**Result:**

```text
$ python scripts/ci/check_deprecated_namespace_imports.py --check-shims
Deprecated namespace import findings: 0
Shim logic violations: 0
PASS
```

### 6. `value_fabric/layer3/api/app_monolith.py` — EDITED (security fix)

Removed `neo4j_uri` from health check dependency details.

### 7. `value_fabric/layer3/api/routes/system.py` — EDITED (security fix)

Removed `neo4j_uri` from health check dependency details; added real Pinecone connectivity probe.

### 8. `.github/workflows/drift-check.yml` — EXTENDED

Added CI steps:

- Security regression drift
- Deprecation drift (with baseline)
- Migration safety drift (with baseline)
- Production-readiness language drift (with baseline)

---

## Drift Categories Now Covered

| Category | Script/Check | Status |
| - | - | - |
| Security regression | `check_security_regressions.py` | Active, passes |
| Deprecation drift | `check_deprecation_drift.py` | Active, passes with baseline (30 baselined, 5 fixed) |
| Migration safety | `check_migration_safety.py` | Active, passes with baseline (156 baselined) |
| Readiness language | `check_readiness_language.py` | Active, passes with baseline (9 baselined) |
| Import/shim drift | `check_deprecated_namespace_imports.py --check-shims` | Active, passes |
| OpenAPI contract drift | `drift-check.yml` + `export_openapi.py` | Already existed, extended |

---

## Drift Categories Still Uncovered (P1/P2)

| Category | Rationale |
| - | - |
| Docker/base-image drift | Detect accidental public Python defaults in production Dockerfiles |
| PYTHONPATH/test-config drift | Prevent repo-root/service-local pytest path collisions |
| Frontend/backend route drift | Detect raw API paths outside approved client modules |
| Observability/metrics conventions | Verify no high-cardinality labels in metrics |
| Full cross-layer integration | Async contract tests across all layer boundaries |

---

## Known Exceptions / Allowlists

| Check | Exception | Reason |
| - | - | - |
| Security regression | `scripts/ci/check_security_regressions.py` self-allowlist | Script's own regex literals trigger false positives |
| Deprecation drift | `scripts/ci/check_deprecation_drift.py` self-allowlist | Script's own regex literals |
| Import drift | `value_fabric/layer3/` dual-role policy | `value_fabric/layer3/` is canonical domain; `services/layer3-knowledge/src/` is deployable wrapper |

---

## ADR-Required Items

1. **Canonical package authority:** Resolve whether `services/layer*-*/src/` or `value_fabric/layer*/` is the authoritative runtime source tree. Layer 3 currently uses a dual-role structure that contradicts `canonical-paths-policy.md`.

2. **Global-vs-tenant entity semantics:** Layer 3 has unresolved ambiguity about when entities are canonical/global vs. tenant-local. The Cypher scope guard enforces tenant filtering, but the semantic model should be explicitly documented.

---

## Baseline Files Created

All baseline files include `reason`, `owner`, and `removal_condition` for every entry.

1. `docs/reference/deprecation-drift-baseline.json` — **30 entries**
   - 3 `utcnow` in shared production code (`tenant_rate_limiter.py`)
   - 7 `utcnow` in Layer 2 production code
   - 1 `utcnow` + 5 `request_type_response` in Layer 4 production code
   - 8 `utcnow` in Layer 4 test code
   - 6 `utcnow` in repo-root test code

2. `docs/reference/migration-safety-baseline.json` — **156 entries**
   - Layer 2 and Layer 4 migration scripts
   - Categories: missing `dry_run`, `print()` in migrations, destructive Cypher without markers, Enterprise-only constraints without fallback notes

3. `docs/reference/readiness-language-baseline.json` — **9 entries**
   - Historical reports and legacy documentation with unqualified readiness claims
   - One explicitly archived document

---

## Production-Readiness Boundary Language

> Anti-drift hardening is complete for the implemented guardrail scope. These checks reduce regression risk and support production-readiness review, but full platform production readiness is not claimed unless all production gates pass with evidence.

---

## Commands to Validate

```bash
# All P0 checks now pass with --strict --use-baseline
python scripts/ci/check_security_regressions.py --strict
python scripts/ci/check_deprecation_drift.py --strict --use-baseline
python scripts/ci/check_migration_safety.py --strict --use-baseline
python scripts/ci/check_readiness_language.py --strict --use-baseline
python scripts/ci/check_deprecated_namespace_imports.py --check-shims --strict

# CI workflow syntax check
python scripts/ci/check_workflow_references.py --workflow-glob drift-check.yml
```
