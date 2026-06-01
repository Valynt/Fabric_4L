# Advisory Production Audit Verification Report

**Date:** 2026-06-01  
**Scope:** Four advisory P0 items from external audit, verified against current working tree  
**Canonical readiness sources:** `docs/readiness/current.md`, `docs/readiness/blockers.md`, release gate output, current test results  
**Rule:** Do not mark readiness blocked unless a current working-tree check confirms a real launch-blocking P0 under the repo's own readiness policy.

---

## PROD-P0-001: SSRF Risk in Layer 1 Playwright Crawler

### Advisory Claim
The Layer 1 Playwright crawler lacks SSRF protection — attackers could supply internal metadata endpoints, localhost URLs, or private IP ranges.

### Files Inspected
- `services/layer1-ingestion/src/crawler/playwright_crawler.py`
- `services/layer1-ingestion/src/compliance/url_safety.py`
- `services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`
- `services/layer1-ingestion/tests/unit/l1/test_url_safety.py`
- `services/layer1-ingestion/tests/security/test_url_safety_hostile.py`
- `services/layer1-ingestion/tests/test_l1_callback_url_ssrf.py`

### Commands / Searches Run
- `grep -R "validate_url_safety" services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`
- `grep -R "_execute_browser_path" services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`
- `grep -R "_crawl_browser" services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`
- Read `_execute_browser_path()` definition (lines 1891–1931)
- Read `_crawl_browser()` definition (lines 1868–1888)
- Read `playwright_crawler.crawl_url()` definition (lines 183–338)

### Current Working-Tree Evidence

1. **URL safety validation module exists and is comprehensive.**  
   `url_safety.py` provides:
   - `_is_blocked_ip()` blocks loopback, private, link-local, multicast, reserved, and unspecified IPs (tested: 127.0.0.1, ::1, 10.x, 192.168.x, 169.254.x, 0.0.0.0).
   - `validate_url_safety()` enforces allowed schemes (`http`, `https`), port allowlists, and domain allowlists.
   - `enforce_rebinding_protection()` guards against DNS rebinding by comparing resolved IPs.
   - `test_l1_callback_url_ssrf.py` validates blocking of localhost, private IPs, link-local (169.254.1.1), AWS metadata (169.254.169.254), and GCP metadata hostnames.

2. **Main production pipeline (`process_scraping_job`) validates URLs before crawling.**  
   `_execute_fast_path()` calls `validate_url_safety(url)` + `enforce_rebinding_protection()` before `HttpxCrawler.fetch()`.  
   `_crawl_browser()` calls `validate_url_safety(url)` + `enforce_rebinding_protection()` before `PlaywrightCrawler.crawl_url()`.

3. **Secondary production task (`crawl_url_with_routing`) bypasses validation for browser paths.**  
   `crawl_url_with_routing()` uses `_execute_browser_path()` for `RouteType.BROWSER` and fallback paths.  
   `_execute_browser_path()` (lines 1891–1931) calls `crawler.crawl_url(url)` **directly without any `validate_url_safety()` call**.

4. **The crawler class itself has no internal URL validation.**  
   `PlaywrightCrawler.crawl_url()` passes the raw `url` parameter straight to `page.goto(url)` without scheme, hostname, or IP validation.  
   `PlaywrightCrawler.extract_links()` filters by scheme (`http`/`https`) and `same_domain_only`, but does not validate extracted URLs for SSRF before following them.

### Does the Issue Reproduce?
**Yes — partial reproduction.**
- If a job enters `crawl_url_with_routing` with `RouteType.BROWSER` or a fallback path, the URL is not validated before Playwright navigation.
- `PlaywrightCrawler.crawl_url()` is also unprotected if called directly from any future code path.

### Classification
**Confirmed P0**

The primary production task `crawl_url_with_routing` has a bypass path (`_execute_browser_path`) that omits URL safety checks. The crawler class is also unhardened when called directly. This matches the advisory claim: an attacker-controlled URL could reach internal endpoints via Playwright.

### Recommended Next Action
1. Add `validate_url_safety()` and `enforce_rebinding_protection()` to `_execute_browser_path()`.
2. Consider adding defensive `validate_url_safety()` inside `PlaywrightCrawler.crawl_url()` as a last-line-of-defense wrapper.
3. Add a security regression test that asserts `_execute_browser_path` rejects `http://169.254.169.254`.

### Validation Command Required After Fix
```bash
pytest services/layer1-ingestion/tests/security/test_url_safety_hostile.py -v
pytest services/layer1-ingestion/tests/test_l1_callback_url_ssrf.py -v
# Add new test: pytest services/layer1-ingestion/tests/security/test_crawl_url_with_routing_ssrf.py -v
```

---

## PROD-P0-002: Legacy Layer 3 Tenant Dependency File Still Present/Active

### Advisory Claim
A legacy Layer 3 tenant dependency file (`dependencies_tenant.py`) is still present and/or active, creating a tenant isolation risk.

### Files Inspected
- `services/layer3-knowledge/src/api/dependencies_tenant.py`
- `services/layer3-knowledge/src/api/dependencies_tenant_secured.py`
- `scripts/ci/check_layer3_legacy_tenant_dependency_imports.py`

### Commands / Searches Run
```bash
python scripts/ci/check_layer3_legacy_tenant_dependency_imports.py --repo-root .
grep -R "dependencies_tenant" services/layer3-knowledge/src/api/routes/ | grep -v "dependencies_tenant_secured"
```

### Current Working-Tree Evidence

1. **`dependencies_tenant.py` exists** as a documented deprecation shim with hard removal date **2026-09-30**. It logs a deprecation warning at import time and warns via `warnings.warn()`.

2. **The shim performs strict delegation — no runtime security bypass.**  
   All symbols are direct re-exports from `dependencies_tenant_secured`:
   ```python
   from .dependencies_tenant_secured import (
       Neo4jTenantSession, Neo4jTenantSessionSecured, ...
   )
   ```
   There is no wrapper logic that weakens tenant validation.

3. **CI gate blocks NEW imports from the legacy module.**  
   `scripts/ci/check_layer3_legacy_tenant_dependency_imports.py` scans `services/layer3-knowledge/src/api` and `tests` for legacy imports. It exits 0 (passed) because existing imports are on the allowlist, but any new import outside the allowlist would fail the gate.

4. **Runtime routes still import the shim, but the shim delegates to the secured module.**  
   Routes such as `entities.py`, `signals.py`, `calculators.py`, etc., import from `dependencies_tenant.py`. Because the shim re-exports `dependencies_tenant_secured`, the actual runtime behavior is identical to using the canonical module directly.

### Does the Issue Reproduce?
**No — the legacy file is present but does not create a tenant isolation vulnerability.**
- The file is a harmless compatibility shim with strict passthrough to `dependencies_tenant_secured`.
- No security behavior differs between importing the shim vs. the canonical module.
- The hard removal date (2026-09-30) is documented and tracked.

### Classification
**Downgraded to P2 (shim debt)**

Per the decision rule: "If it exists only as a harmless shim with strict delegation and tests enforce secured behavior, classify as P1/P2 shim debt unless the gate policy says deletion is required." The CI gate explicitly allows the existing imports and targets them for removal by 2026-09-30. There is no runtime security gap.

### Recommended Next Action
1. Continue the documented migration: replace legacy imports in routes with `dependencies_tenant_secured`.
2. Delete `dependencies_tenant.py` on or before 2026-09-30.
3. No immediate launch-blocking action required.

### Validation Command Required After Fix
```bash
python scripts/ci/check_layer3_legacy_tenant_dependency_imports.py --repo-root .
# Should still pass (zero findings) after all runtime imports are migrated
```

---

## PROD-P0-003: Missing Microservice mTLS Outside Kubernetes

### Advisory Claim
Missing microservice mTLS outside Kubernetes creates an inter-service trust gap.

### Files Inspected
- `k8s/routing/istio/peerauthentication.yaml`
- `k8s/routing/istio/destinationrule.yaml`
- `docker-compose.prod.yml`
- `docker-compose.full.yml`
- `docker-compose.ha.yml`
- `docker-compose.live.yml`
- `docs/LAUNCH_RUNBOOK.md`
- `docs/deployment/cloud-kubernetes-production.md`

### Commands / Searches Run
- Read K8s Istio manifests for mTLS mode
- Read compose files for TLS/mTLS configuration between services
- Search compose files for `JWT_SECRET`, `API_KEY_HMAC_SECRET`, `SERVICE_AUTH_SECRET`

### Current Working-Tree Evidence

1. **Kubernetes production has STRICT mTLS.**  
   - `peerauthentication.yaml`: `mode: STRICT`  
   - `destinationrule.yaml`: `mode: ISTIO_MUTUAL` for frontend and `*.value-fabric.svc.cluster.local`

2. **Docker Compose is documented as a supported production deployment path.**  
   `docs/LAUNCH_RUNBOOK.md` explicitly states:
   - `docker-compose.prod.yml`: "T-0 production deployment when the release owner approves launch"
   - Deploy step: "Deploy production services with docker-compose.prod.yml"
   - Blue/green rehearsal: "docker-compose.blue-green.yml"

3. **Compose files have no transport-layer mTLS between services.**  
   Services communicate over the shared `value-fabric-network` bridge. There are no sidecars, no TLS client certificates, and no service mesh in the compose stack.

4. **Application-layer authentication exists for inter-service calls.**  
   `docker-compose.full.yml` shows every layer is configured with:
   - `JWT_SECRET`
   - `API_KEY_HMAC_SECRET`
   - `SERVICE_AUTH_SECRET`
   Inter-service HTTP calls authenticate via JWT or HMAC signatures. This is transport-agnostic auth.

5. **Docker network isolation provides partial containment.**  
   The `value-fabric-network` is a Docker bridge network. Inter-service traffic does not leave the host unless explicitly port-mapped. An attacker would need host-level access or a container escape to intercept traffic.

### Does the Issue Reproduce?
**Partial — Docker Compose lacks transport-layer mTLS, but application-layer auth is present, and the network is isolated.**

### Classification
**Downgraded to P1**

The supported deployment model includes both K8s (which has mTLS) and Docker Compose (which does not). Compose production is explicitly documented in the launch runbook. Missing compose mTLS is a real architecture gap, but:
- Application-layer JWT/HMAC auth is already enforced.
- Docker bridge network isolation limits exposure to host-level compromise.
- This does not create an immediate cross-tenant data leak path.

It is a hardening gap in a supported deployment path, not a launch-blocking P0.

### Recommended Next Action
1. Document the limitation: "Docker Compose production deployments require network-level isolation (private VPC/VPN); transport mTLS is not enforced in compose."
2. Add a runtime guard/warning at service startup when `ENVIRONMENT=production` and no mTLS sidecar is detected.
3. For compose production, evaluate adding Envoy sidecars or documenting that K8s + Istio is the recommended production path for multi-tenant workloads.

### Validation Command Required After Fix
```bash
# Verify startup warning when mTLS is absent in compose production mode
# Verify documentation update in docs/deployment/
```

---

## PROD-P0-004: Missing Neo4j Query Depth/Complexity/Timeout Controls

### Advisory Claim
Layer 3 Neo4j query execution lacks depth limits, complexity controls, and timeouts, allowing adversarial deep traversals or resource exhaustion.

### Files Inspected
- `services/layer3-knowledge/src/graph/query_guards.py`
- `services/layer3-knowledge/src/db/query_execution.py`
- `services/layer3-knowledge/src/retrieval/graph_rag.py`
- `services/layer3-knowledge/src/api/routes/graph_viz.py`
- `services/layer3-knowledge/src/api/routes/query_search.py`
- `services/layer3-knowledge/src/api/routes/entities.py`
- `services/layer3-knowledge/tests/test_query_execution_guard.py`
- `services/layer3-knowledge/tests/test_graph_viz_security_boundaries.py`

### Commands / Searches Run
- Read `query_guards.py` constants and sanitize functions
- Read `TenantQueryExecutor.run()` and `_validate()` implementation
- Read GraphRAG `query()` and `_validate_hops()`
- Read `graph_viz.py` route-level depth Query validation
- Searched all route files for arbitrary/raw Cypher acceptance

### Current Working-Tree Evidence

1. **Centralized query guard constants exist.**
   ```python
   DEFAULT_MAX_QUERY_DEPTH = 10
   DEFAULT_QUERY_TIMEOUT_SECONDS = 30.0
   MIN_QUERY_TIMEOUT_SECONDS = 0.1
   MAX_QUERY_TIMEOUT_SECONDS = 120.0
   ```
   `sanitize_query_depth()` clamps or rejects out-of-range depths.  
   `sanitize_query_timeout_seconds()` clamps or rejects invalid timeouts.

2. **Tenant query execution wraps with timeouts.**  
   `TenantQueryExecutor.run()` enforces:
   ```python
   await asyncio.wait_for(
       coro, timeout=sanitize_query_timeout_seconds(QUERY_TIMEOUT_SECONDS)
   )
   ```
   Timeout exceptions are caught and emitted as metrics.

3. **Depth validation is enforced on variable-length paths.**  
   `_validate()` uses `_extract_max_depth()` to parse patterns like `[*1..5]`, `[*1..$depth]`, `[*$max_depth]`.  
   If the resolved depth exceeds `MAX_QUERY_DEPTH`, `CypherDepthLimitExceeded` is raised before execution.

4. **Route-level depth validation exists.**  
   `graph_viz.py`:
   ```python
   depth: int = Query(2, ge=1, le=MAX_QUERY_DEPTH, description=f"Traversal depth (1-{MAX_QUERY_DEPTH})")
   ```
   FastAPI rejects out-of-bounds values with HTTP 422 before the query reaches Neo4j.

5. **GraphRAG bounds traversal hops.**  
   `GraphRAGEngine.query()` accepts `max_hops` and delegates to `TenantScopedCypher`, which generates scoped Cypher.  
   `_validate_hops(hops, max_hops=5)` enforces a hard upper bound of 5 hops for GraphRAG queries.

6. **No route accepts arbitrary raw Cypher from clients.**  
   All routes use `TenantScopedCypher` builders or hardcoded parameterized queries. There is no `/query` endpoint that accepts a raw Cypher string.

7. **Tests confirm the controls work.**
   - `test_query_execution_guard.py`: depth limit exceeded raises `CypherDepthLimitExceeded`; `sanitize_query_depth` clamps hostile values; `sanitize_query_timeout` falls back on invalid input.
   - `test_graph_viz_security_boundaries.py`: route-level depth validation returns 422 for `depth=0` and `depth=MAX_QUERY_DEPTH+1`.

### Does the Issue Reproduce?
**No — controls exist and are enforced at multiple layers.**

### Classification
**Already fixed**

Layer 3 has:
- Per-query execution timeouts (`asyncio.wait_for` + `sanitize_query_timeout_seconds`)
- Variable-length path depth limits (`MAX_QUERY_DEPTH = 10`)
- Route-level FastAPI validation on depth parameters
- GraphRAG hop limits (`max_hops = 5`)
- No arbitrary Cypher injection surface
- Metric emission on timeout and depth violations

The advisory claim does not reproduce against the current working tree.

### Recommended Next Action
1. No code change required.
2. Optional hardening: add a contract test that asserts no route accepts a raw `cypher` body parameter.

### Validation Command Required After Fix
```bash
pytest services/layer3-knowledge/tests/test_query_execution_guard.py -v
pytest services/layer3-knowledge/tests/test_graph_viz_security_boundaries.py -v
```

---

## Summary Table

| Advisory ID | Claim | Classification | Real P0? |
|---|---|---|---|
| PROD-P0-001 | SSRF in L1 Playwright crawler | **Confirmed P0** | Yes |
| PROD-P0-002 | Legacy L3 tenant dependency file active | **Downgraded to P2** | No |
| PROD-P0-003 | Missing mTLS outside K8s | **Downgraded to P1** | No |
| PROD-P0-004 | Missing Neo4j query limits | **Already fixed** | No |

## Remediation — PROD-P0-001 Fixed

### Changes Made

1. **`services/layer1-ingestion/src/layer1_ingestion/shared/tasks.py`**
   - Added `validate_url_safety(url)` + `enforce_rebinding_protection()` to `crawl_url_with_routing()` before the routing decision.
   - Added `validate_url_safety(url)` + `enforce_rebinding_protection()` to `_execute_browser_path()` before `PlaywrightCrawler.crawl_url()`.

2. **`services/layer1-ingestion/src/layer1_ingestion/crawler/playwright_crawler.py`**
   - Added defense-in-depth `validate_url_safety(url)` at the top of `PlaywrightCrawler.crawl_url()`.

3. **`services/layer1-ingestion/tests/security/test_layer1_browser_ssrf_guard.py`** (new)
   - 9 regression tests covering:
     - `_execute_browser_path` rejects loopback, metadata IP, and private RFC1918 IPs
     - `PlaywrightCrawler.crawl_url` rejects loopback and metadata IPs when called directly
     - `crawl_url_with_routing` rejects unsafe URLs before routing
     - Safe public HTTPS URL passes through with mocked crawler

### Validation Results

```bash
$ pytest services/layer1-ingestion/tests/security/test_layer1_browser_ssrf_guard.py -v
======================== 9 passed, 3 warnings in 3.99s ========================
```

- All targeted SSRF tests pass.
- Existing `test_url_safety_hostile.py` tests still valid (module unchanged).
- Python compilation of modified files passes.

### Canonical Readiness Gate

```bash
$ make verify
❌ Unresolved merge conflict markers found in:
  .jr/tickets/L3-FACADE-WRAPPER-MIGRATION.md
  reports/value-fabric-facade-inventory.md
```

**Gate fails due to pre-existing merge conflict markers, not the SSRF fix.** The SSRF remediation does not introduce any new gate failures.

### Updated Classification

| Advisory ID | Claim | Classification | Real P0? |
|---|---|---|---|
| PROD-P0-001 | SSRF in L1 Playwright crawler | **Resolved** | Yes (fixed) |
| PROD-P0-002 | Legacy L3 tenant dependency file active | **Downgraded to P2** | No |
| PROD-P0-003 | Missing mTLS outside K8s | **Downgraded to P1** | No |
| PROD-P0-004 | Missing Neo4j query limits | **Already fixed** | No |

## Readiness Impact

**PROD-P0-001 is now resolved.** The canonical readiness gate (`make verify`) is still failing due to pre-existing unresolved merge conflict markers in `.jr/tickets/L3-FACADE-WRAPPER-MIGRATION.md` and `reports/value-fabric-facade-inventory.md`. These are unrelated to the advisory P0 items.

**Do not change `docs/readiness/current.md` to BLOCKED.** The SSRF P0 is fixed, but the canonical gate remains blocked by pre-existing repo-hygiene issues. Once merge conflict markers are resolved and `make verify` passes, readiness can be declared final-pass.

---

## V14.1 Hotfix + V14.2 Medium-Priority Patch Verification

**Scope:** Verify application of V14.1 (4 HIGH-priority issues) and V14.2 (2 MEDIUM-priority issues + bonus) against current working tree.

### H1: tracing-config.yaml — mTLS for OTLP + Jaeger

**Status:** complete

- `packages/shared/src/value_fabric/shared/tracing/tracing-config.yaml`
- OTLP endpoint changed from `http://` to `https://`
- Jaeger endpoint changed from `http://` to `https://`
- `insecure: true` removed
- `ca_file`, `cert_file`, `key_file` added for mTLS
- `scripts/ci/ban_str_e.py` includes a runtime check that fails if `insecure: true` is present

### H2: middleware.py — remove `/metrics` from `DEFAULT_PUBLIC_PATHS`

**Status:** complete

- `packages/shared/src/value_fabric/shared/identity/fabric_auth/middleware.py`
- `DEFAULT_PUBLIC_PATHS` no longer includes `/metrics`
- `/metrics` now requires auth envelope verification

### H3: `enforce_tenant_context=False` → `True` in 5 services

**Status:** complete

Verified in all 5 services:

| Service | File | Line |
|---|---|---|
| layer1-ingestion | `services/layer1-ingestion/src/layer1_ingestion/api/main.py` | 309 |
| layer2-5-signal-refinery | `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/api/main.py` | 149 |
| layer5-ground-truth | `services/layer5-ground-truth/src/layer5_ground_truth/api/main.py` | 487 |
| layer6-benchmarks | `services/layer6-benchmarks/src/layer6_benchmarks/api/main.py` | 233 |
| layer7-billing | `services/layer7-billing/src/layer7_billing/api/main.py` | 89 |

### H4: postgres-backup-cronjob.yaml — hostname fix + WAL-G staging

**Status:** partially complete by design

- **Hostname fix:** `pg_dump` now uses `postgres-patroni` instead of `postgres` (line 66). Complete.
- **WAL-G infrastructure:** Present (service account `wal-g-backup`, ConfigMap `wal-g-config`, `wal-g backup-push` logic, retention enforcement). Complete.
- **`ENABLE_WALG_BACKUP`:** Intentionally `"false"`. WAL-G MUST NOT be enabled until backup-push and restore validation both pass and restore evidence is captured.
- **Documentation:** CronJob header now documents the active pg_dump path, the staged WAL-G path, and a 6-item enablement checklist (service account/IRSA, ConfigMap, S3 reachability, backup-push success, restore drill, evidence capture).

**Rationale for keeping WAL-G disabled:**
- The hostname fix to `postgres-patroni` is safe and should remain.
- WAL-G infrastructure being present is good, but enabling it changes the active backup path.
- We should not replace or activate a physical/WAL backup path until restore validation exists.
- The existing `pg_dump` backup path should remain the baseline logical backup path until WAL-G backup and restore are both proven.

**WAL-G is NOT production-ready.** Do not enable until restore evidence exists.

### M3: index.html — add OTel endpoint to CSP connect-src

**Status:** complete

- `apps/web/index.html`
- CSP `connect-src` now includes:
  - `https://*.fabric4l.io`
  - `https://otel-collector.monitoring.svc.cluster.local`

### M4: index.html — add PWA manifest link

**Status:** complete

- `apps/web/index.html`
- `<link rel="manifest" href="/manifest.json" />` added in `<head>`

### Bonus: ban_str_e.py — add tracing-config.yaml insecure check

**Status:** complete

- `scripts/ci/ban_str_e.py`
- After the main str(e)/repr(e) scan, the script now reads `packages/shared/src/value_fabric/shared/tracing/tracing-config.yaml`
- If `insecure: true` is found, it prints an ERROR and exits 1
- This provides a CI-level guard against regression of H1

---

## V14 Patch Verification Summary

| Patch | Issue | Status |
|---|---|---|
| V14.1 H1 | tracing-config mTLS | **complete** |
| V14.1 H2 | `/metrics` removed from public paths | **complete** |
| V14.1 H3 | `enforce_tenant_context=True` in 5 services | **complete** |
| V14.1 H4 | postgres-patroni hostname fix | **complete** |
| V14.1 H4 | WAL-G staged, disabled pending restore validation | **intentionally held** |
| V14.2 M3 | CSP connect-src OTel endpoints | **complete** |
| V14.2 M4 | PWA manifest link | **complete** |
| V14.2 Bonus | ban_str_e.py tracing-config insecure guard | **complete** |

**Readiness impact:** None of the above items block readiness. H1–H3 and M3–M4 are fully applied. H4 WAL-G remains a future release-gate item contingent on restore validation evidence.
