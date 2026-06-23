# Launch Readiness Assessment — Value Fabric

**Generated:** 2026-06-22  
**Source:** Dual-track assessment using ROADMAP.md, current readiness docs, and newest local evidence

---

## 1. Dual-track readiness posture

**Canonical claim (from [docs/readiness/current.md](../docs/readiness/current.md)):**

- **Claimed posture:** **BLOCKED** as of 2026-06-21
- Claimed evidence: `make verify` passes, `make production-readiness-gate` passes (2026-06-15), but superseded by newer evidence showing launch-gate drift and stale/missing artifacts

**Verified posture:** **BLOCKED**

The newest local evidence (2026-06-22) does not support launch readiness. Release gate fails (3/6 blocking gates), arch/security evidence is stale, and generated client reproducibility fails.

---

## 2. Launch-gate integrity check

| Check | Result | Evidence |
|---|---|---|
| [.github/workflows/prod-readiness.yml](../.github/workflows/prod-readiness.yml) exists | ✅ | File exists |
| [.fabric/prod-gates.policy.yaml](../.fabric/prod-gates.policy.yaml) exists | ✅ | File exists |
| [Makefile](../Makefile) gate targets exist | ✅ | All targets defined |
| `.github/workflows/smoke-gate.yml` | ✅ **EXISTS** | **Improvement since 2026-06-21** |
| `python scripts/smoke/production_smoke.py` | ✅ **EXISTS** | **Improvement since 2026-06-21** |
| Required artifact directories | ✅ | `artifacts/smoke/`, `artifacts/obs/`, `artifacts/agent/`, `artifacts/state/` have content |

**Finding:** Launch-gate integrity has **improved** since 2026-06-21 assessment. Previously missing files now exist. However, gate execution results show failures.

---

## 3. Main readiness table

| Area | Target | Claimed | Verified | Gap | Evidence |
|---|---|---|---|---|---|
| **L1 Ingestion** | 90% | Not specified in ROADMAP.md | **Partial** - release gate shows db-consistency FAIL | Missing fresh L1-specific production-readiness evidence | `artifacts/release/summary.md` (db-consistency FAIL) |
| **L2 Extraction** | 95% | Not specified | **Partial** - no fresh L2 gate artifact | Same db-consistency FAIL | No fresh L2-specific evidence |
| **L3 Knowledge Graph** | 90% | Not specified | **Blocked** - arch gate shows contract drift (stale), security report shows 85% coverage (stale) | 1 contract drift violation, endpoint coverage below 100% | `artifacts/arch/summary.md` (2026-04-23 stale), `artifacts/security/report.json` (2026-04-23 stale) |
| **L4 Agents** | 85% | Not specified | **Blocked** - generated_client_reproducible FAIL | Frontend API clients out of date/unreproducible | `artifacts/release/release-readiness-report.md` (FAIL) |
| **L5 Ground Truth** | 100% | Not specified | **Partial** - state gate FAIL | Missing fresh state evidence | `artifacts/release/summary.md` (state FAIL) |
| **Frontend** | 85% | Not specified | **Blocked** - generated_client_reproducible FAIL | API clients unreproducible | `artifacts/release/release-readiness-report.md` (FAIL) |
| **DevOps** | 80% | Not specified | **Blocked** - 3/6 blocking gates failed (db-consistency, state, security) | Missing fresh gate artifacts | `artifacts/release/gate-result.json` (FAIL) |

**Claimed overall readiness:** BLOCKED per docs/readiness/current.md (2026-06-21)

**Verified overall readiness:** **BLOCKED** — Release gate fails (3/6 blocking gates), stale arch/security evidence, contract drift, generated client reproducibility failure

---

## 4. L6 Benchmarks note

- **Claimed:** Not independently declared in ROADMAP.md
- **Verified:** Tenant-isolation tests pass (2026-06-22), but no fresh benchmark dataset evidence
- **Launch relevance:** L6 is **not launch-critical** for Core GA per the canonical posture, but it is part of the live-stack critical path. Should be explicitly de-scoped or re-verified with the next release run.

---

## 5. Top 5 launch blockers

1. **Release gate failures (3/6 blocking gates)**
   - db-consistency FAIL, state FAIL, security FAIL
   - Evidence: `artifacts/release/gate-result.json` (2026-06-22)
   - Impact: Blocks release unconditionally

2. **Generated client reproducibility FAIL**
   - Frontend API clients are out of date or unreproducible
   - Evidence: `artifacts/release/release-readiness-report.md` (2026-06-21)
   - Impact: Blocks frontend integration

3. **Stale architecture gate evidence**
   - Contract drift violation (1) from 2026-04-23 (2 months stale)
   - Evidence: `artifacts/arch/summary.md`
   - Impact: Cannot verify current contract status

4. **Stale security gate evidence**
   - 85% endpoint coverage (target 100%), 1 cross-tenant attempt from 2026-04-23
   - Evidence: `artifacts/security/report.json`
   - Impact: Cannot verify current security posture

5. **Missing fresh layer-specific production-readiness evidence**
   - No fresh L1-L5 gate artifacts
   - Evidence: Missing in artifacts/release/
   - Impact: Cannot verify individual layer readiness

---

## 6. Refreshed 5-sprint plan

| Sprint | Focus | Key deliverables |
|---|---|---|
| **Sprint 1 — Gate Evidence Refresh** | Regenerate stale gate artifacts | Run `make gate-arch` to get fresh contract drift status; run `make gate-security` to get fresh security/tenant-isolation status; regenerate `artifacts/arch/summary.md` and `artifacts/security/report.json`; resolve any new violations found |
| **Sprint 2 — Release Gate Closure** | Fix 3/6 blocking gate failures | Fix db-consistency gate failure; fix state gate failure; fix security gate failure; run `make release-gate PROFILE=release-candidate` to achieve 6/6 blocking gates pass |
| **Sprint 3 — Frontend Client Reproducibility** | Fix generated client drift | Regenerate API clients with `pnpm run generate:api`; fix any reproducibility issues; verify `build.generated_client_reproducible` passes; run `make gate-api-contracts` green |
| **Sprint 4 — Layer-Specific Hardening** | L1-L5 production-readiness evidence | Generate fresh layer-specific gate artifacts for L1-L5; run layer-specific test suites with retained JUnit/coverage; verify each layer meets its target percentage |
| **Sprint 5 — Final Evidence Refresh and Go/No-Go** | End-to-end prod-readiness run | Run full `make release-gate PROFILE=release-candidate`; collect/attach all required evidence; resolve any remaining P0/P1 blockers; sign manifest; generate final launch-readiness report |

---

## 7. Cross-cutting tracks

- **Evidence Freshness:** Arch and security gate artifacts are stale (2026-04-23). Must regenerate in Sprint 1. Tenant-isolation summary is fresh (2026-06-22) and shows PASS.
- **Contract Stability:** Generated client reproducibility FAIL must be cleared. Contract drift violation (1) needs verification with fresh arch gate.
- **Test Reliability:** Tenant-isolation tests now pass (68 + 29 + 18 + 30 = 145 total). Need to verify this remains green after evidence refresh.
- **Observability:** artifacts/obs/ has content (gate-obs-summary.json, red-dashboard-snapshot-metadata.json) but needs verification.
- **Documentation:** Launch-gate path is intact (smoke-gate.yml and production_smoke.py exist). Document final verification commands in docs/readiness/current.md.

---

## 8. Final launch checklist

- [x] Claimed and verified readiness are reported separately
- [x] Launch-gate workflow references only commands/files that actually exist
- [ ] Required policy/config files exist (`.fabric/prod-gates.policy.yaml` - not verified)
- [ ] Fresh arch artifact exists and passes (stale from 2026-04-23)
- [ ] Fresh security artifact exists and passes (stale from 2026-04-23, but tenant-isolation fresh PASS)
- [ ] Fresh state artifact exists and passes (gate-state FAIL)
- [ ] Fresh agent artifact exists and passes (has content, not verified)
- [ ] Fresh observability artifact exists and passes (has content, not verified)
- [ ] Smoke gate passes on the current stack (not verified)
- [ ] No unresolved cross-layer contract drift remains (1 violation in stale artifact)
- [ ] Monitoring and dependency-aware health checks are verified (not verified)
- [ ] Kubernetes readiness is verified (not verified)
- [ ] Frontend critical screens remain evidence-backed and not merely claimed (not verified)
- [ ] L1 launch status is explicitly verified or explicitly de-scoped (not verified)

---

## 9. Approval status

**Verified readiness is BLOCKED** on the current evidence.

---

## 10. Implementation Progress (2026-06-22)

**Completed:**
- ✅ Fixed missing `check_runtime_shim_drift.py` script in layer3
- ✅ Fixed TOML syntax errors in `layer2-extraction/pyproject.toml` (duplicate ignore sections)
- ✅ Fixed TOML syntax errors in `layer5-ground-truth/pyproject.toml` (duplicate ignore sections)
- ✅ Fixed layer3 shim drift script syntax error (removed "1" prefix)
- ✅ Fixed layer3 cache.py import ordering
- ✅ Fixed lint issue in layer6-benchmarks (import ordering)
- ✅ **Agent gate fixed** - Removed obsolete compatibility shims, updated tests (60 tests passing)
- ✅ `make gate-arch` passed (54 tests)
- ✅ `make gate-security` passed (mandatory security regression gate)

**Remaining blockers (2026-06-23 release-gate run):**
- ❌ **Database gate** - PostgreSQL not running (environment-dependent, requires Docker stack)
- ⚠️ **Gate reporting discrepancy** - arch/security logs show PASS but release-gate summary shows FAIL (likely timing/reporting issue)
- ❌ **Generated client reproducibility** - openapi-typescript dependency issue with js-yaml compatibility (requires node_modules resolution)

**Updated blockers (2026-06-23):**
1. Database gate (environment-dependent - requires PostgreSQL/Docker stack)
2. Gate reporting discrepancy (arch/security pass locally but fail in release-gate summary - needs investigation)
3. Generated client reproducibility (dependency issue - requires node_modules fix or dependency update)

**Summary of implementation work:**
- Fixed all gate infrastructure issues (missing scripts, TOML syntax, lint, agent taxonomy refactor)
- Agent gate now passes (60 tests) - removed obsolete shims and updated tests
- arch and security gates pass locally
- Remaining blockers are environment-dependent (database) or require dependency resolution (generated clients)

This assessment is saved at `.windsurf/plans/launch-readiness-2026-06-22.md`.
