# Launch Blocker Board

_Last updated: 2026-06-01 (PROD-P0-001 SSRF fix applied)_
_Canonical readiness source: [`docs/readiness/current.md`](current.md) — 97%_

**Launch Readiness:** **CONDITIONALLY UNBLOCKED — service-backed skipped-test evidence pending**

All documented P0 blockers have passing local evidence or have been verified resolved in the current working tree. Final launch sign-off still requires running the skipped service-backed tenant isolation tests in CI/staging with PostgreSQL and Redis available.

**Definitions:**
- **P0** — Release-blocking. Pilot cannot launch until resolved.
- **P1** — Must fix before external demo or tenant onboarding expansion.
- **P2** — Post-launch hardening. Required before broad GA.

Primary evidence source: `reports/current-readiness-p0-remediation-2026-06-01.md`

---

## P0 — Release blockers

| ID | Area | Blocker | Owner | Status | Evidence / Link |
|---|---|---|---|---|---|
| P0-0 | Repo hygiene | ~~Unresolved Git merge conflict markers in 9 Python files~~ | — | ✅ **RESOLVED** | `make check-conflict-markers` passes as of 2026-05-18 |
| P0-1 | Security / RLS | ~~RLS enforcement test regression — `test_remediation_migrations_do_not_reintroduce_null_visibility` fails; NULL tenant_id visibility may have been reintroduced by a newer migration~~ | — | ✅ **RESOLVED** | `pytest tests/security/test_rls_enforcement.py -q --no-mandatory-dep-check` passes 26/26 as of 2026-06-01. No migration reintroduces NULL visibility. |
| P0-2 | Architecture | ~~Architecture conformance suite has 5 failures — blocks `gate-arch` (blocking gate per `.fabric/prod-gates.policy.yaml`)~~ | — | ✅ **RESOLVED** | `pytest tests/arch/ -q --no-mandatory-dep-check` passes 35/35 as of 2026-06-01. Root causes: merge conflict markers in 2 files, stale Layer 6 sentinel paths, stale L4 shim paths in tenant architecture test config, stale sync-engine baseline path, dead `database.py` duplicate. |
| P0-3 | Security / Cache | ~~Redis cache tenant isolation gate is false-green — all 14 tests in `test_redis_tenant_isolation.py` fail with `TypeError: '>=' not supported between instances of 'AsyncMock' and 'int'`; invariant is untested in practice~~ | — | ✅ **RESOLVED** | `pytest tests/cache/test_redis_tenant_isolation.py -q --no-mandatory-dep-check` passes 16/16 as of 2026-06-01. Root cause was stale patch path `value_fabric.layer3.api.cache` → fixed to `src.api.cache`. |
| P0-4 | Infra / K8s | ~~Staging `kustomization.yaml` still contains placeholder image digests (`sha256:1111...7777`) — digest guard now blocks staging promotion CI~~ | — | ✅ **RESOLVED** | `scripts/ci/test_placeholder_digest_detection.sh` passes 9/9 and `scripts/ci/check-k8s-image-digests.sh` passes as of 2026-06-01. Both staging overlays contain real immutable SHA256 digests. |
| PROD-P0-001 | Security / SSRF | ~~Layer 1 browser/fallback crawler path (`_execute_browser_path`) bypassed URL safety validation — unsafe URLs could reach internal endpoints via Playwright~~ | — | ✅ **RESOLVED** | `pytest services/layer1-ingestion/tests/security/test_layer1_browser_ssrf_guard.py -v` passes 9/9 as of 2026-06-01. Validation added at three trust boundaries: `crawl_url_with_routing`, `_execute_browser_path`, and `PlaywrightCrawler.crawl_url`. |

### P0 Follow-up: Service-Backed Validation Required

The following tests were **skipped** during local verification because PostgreSQL and Redis services are not available in the bare development environment. They must be run in a service-backed CI or staging environment before final production readiness sign-off:

| Test File | Skipped Tests | Reason | Required Environment |
|---|---|---|---|
| `tests/security/test_tenant_isolation.py` | Cache isolation tests (3) | Redis unavailable locally | `docker compose up redis` |
| `tests/security/test_tenant_isolation.py` | RLS enforcement tests (3) | PostgreSQL unavailable locally | `docker compose up postgres` |
| `tests/security/test_tenant_isolation.py` | Endpoint-dependent tests (3) | Full app routes not mounted | Complete app with routes |

**Required outcome:** All skipped tests must either pass or be explicitly justified with environment evidence before final sign-off.

---

## P1 — Must fix before external demo

| ID | Area | Item | Owner | Status | Evidence / Link |
|---|---|---|---|---|---|
| P1-1 | CI / Security | Mandatory security regression CI job (`mandatory-security-regression` in `security-gates.yml`) not yet a required status check in GitHub branch protection | — | 🔴 Open | `fabric_audit/sprint4_launch_decision_package.md`; configure in GitHub branch protection settings |
| P1-2 | Auth | Unauthenticated route outside allowlist: `GET /workflows/{workflow_id}/state/errors` reachable without auth | — | 🔴 Open | `contracts/route-auth-allowlist.yaml` — add auth dependency or explicit allowlist entry with rationale |
| P1-3 | Test infra | Contract test collection errors in 4 L3 files prevent local contract-suite execution (`test_entity_contract.py`, `test_l3_provenance_audit_contract.py`, `test_l3_route_alias_parity.py`, `test_layer3_graph_deprecation_contract.py`) | — | 🔴 Open | Import-time drift between contract test setup and current L3 code paths |
| P1-4 | Test infra | Schemathesis × pytest-xdist incompatibility crashes `tests/contract` run with `WorkerController has no attribute 'workeroutput'` | — | 🔴 Open | Pin schemathesis/xdist versions or run schemathesis tests serially (`-p no:xdist`) |
| P1-5 | Testing | Connection-pooling and ACID property tests absent — required before multi-tenant GA | — | 🔴 Open | `PRODUCTION_READINESS_ASSESSMENT_2026-05-05.md` §2.4 |
| P1-6 | Security | P0 security test gaps: GovernanceMiddleware resolution-order adversarial tests, RequestContext immutability, tier-aware isolation, audit event emission completeness | — | 🔴 Open | Carried from 2026-05-05 assessment |

---

## P2 — Post-launch hardening

| ID | Area | Item | Owner | Status | Evidence / Link |
|---|---|---|---|---|---|
| P2-1 | Auth | OAuth authorization flow for CRM integrations | — | 🔴 Open | `PRODUCTION_READINESS_ASSESSMENT_2026-05-05.md` §6.3 |
| P2-2 | Infra | Background sync → Celery/Redis queue (currently `asyncio.create_task`) | — | 🔴 Open | Layer 1 Celery wiring gap |
| P2-3 | Testing | Comprehensive E2E coverage for critical flows | — | 🔴 Open | — |
| P2-4 | Data | Dedicated `sync_jobs` history table | — | 🔴 Open | — |
| P2-5 | Observability | Prometheus export for all metrics + full SLO/error-budget monitoring | — | 🔴 Open | `gate-obs` advisory; SLO monitoring is GA blocker |
| P2-6 | Ops | Disaster recovery rehearsal | — | 🔴 Open | — |
| P2-7 | Security | Penetration testing | — | 🔴 Open | — |
| P2-8 | Infra / K8s | K8s image digest pinning + admission-time validation (Kyverno/OPA Gatekeeper) | — | 🔴 Open | Digest guard in CI is a partial mitigation; cluster-side enforcement still needed |
| P2-9 | Contract debt | Canonical contract compliance ~58% (~449 active violations) | — | 🔴 Open | `reports/CONTRACT_AUDIT_REPORT.md`; in-flight migration backlog |
| P2-10 | Frontend | 12 placeholder items blocked on backend endpoints (L2 extraction disabled, L3 entity creation not exposed) | — | 🔴 Open | `reports/FRONTEND_STABILIZATION_REPORT_2026-05-06.md` §1–3 |

---

## Sprint 0 Closures (2026-05-18)

| Item | Resolution |
|---|---|
| P0-0 Merge conflicts | ✅ Resolved — `make check-conflict-markers` passes |
| Layer 3 `VaultSourceNotSupportedError` not defined | ✅ Fixed — `manager.py` now defines the class and raises it; all 7 vault tests pass |
| Digest guard not wired into CI | ✅ Fixed — `environment-promotion.yml` now blocks staging + prod deploys on placeholder digests |
| `database.py` 501 → 422 + DeprecationWarning | ✅ Already done (pre-Sprint 0) — confirmed by test suite |
| `kustomization.yaml` prod placeholder digests | ✅ Already done (pre-Sprint 0) — confirmed by guard script |
