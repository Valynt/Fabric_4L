# Release Gate Report — Sprint 5 + Sprint 6

**Date:** 2026-05-18
**Scope:** Auth/security (Sprint 5) + Infra/deployment (Sprint 6)
**Auditor:** Ona (automated + source review)

---

## P0 Blockers

**None.** All Sprint 5 and Sprint 6 acceptance criteria are met.

---

## Sprint 5 — Auth, Tenant Isolation, Security

### Auth Stack

| Item | Status |
|---|---|
| Layer 4 (`GovernanceMiddleware` + OIDC/PKCE) is the production auth path | ✅ |
| `services/api` (JWT+bcrypt) classified as standalone risk | ✅ |
| Cross-stack JWT token shape compatibility tested | ✅ |
| Cross-stack drift documented in `reports/SECURITY_AUDIT_SPRINT5.md` | ✅ |

### Route Protection

| Item | Status |
|---|---|
| `governance_workflows.py` GET routes require `require_authenticated` | ✅ |
| `governance_workflows.py` POST routes require `require_content_admin` | ✅ |
| Gate decision endpoint requires `require_content_admin` | ✅ |
| `decision_by` is server-derived from `ctx.user_id` | ✅ |

### Tenant Isolation

| Item | Status |
|---|---|
| Harness run cross-tenant → 404 | ✅ |
| Gate cross-tenant → 404 | ✅ |
| Checkpoint cross-tenant → 404 | ✅ |
| Validation cross-tenant → 403/404 | ✅ |
| L5 org mapping scoped to tenant | ✅ |
| Frontend X-Tenant-ID header spoof → 403 | ✅ |

### Security Smoke

| Check | Status |
|---|---|
| Missing tenant context → 401/422 | ✅ |
| Wrong tenant → 404 | ✅ |
| Body `tenant_id` ignored | ✅ |
| `decision_by` server-derived | ✅ |
| No secrets in structured log output | ✅ |

### Billing and Provider Posture

| Item | Status |
|---|---|
| Billing routes fail closed with HTTP 402 `billing_not_configured` | ✅ |
| Missing `STRIPE_SECRET_KEY` does not crash app | ✅ |
| Anthropic raises `ProviderNotImplementedError` (typed, not bare) | ✅ |
| Enrichment fails closed without `ENRICHMENT_MOCK_MODE=true` | ✅ |
| Mock enrichment tagged with `mock=true` | ✅ |

---

## Sprint 6 — Infra, Deployment, Observability

### K8s Image Paths

| Item | Status |
|---|---|
| `k8s/base/kustomization.yaml` uses `ghcr.io/<org>/<service>` pattern | ✅ |
| No personal registry hardcoded | ✅ |

### Placeholder Digest Guard

| Item | Status |
|---|---|
| `k8s/envs/prod/kustomization.yaml` contains no placeholder digests | ✅ |
| `k8s/envs/prod/kustomization.yaml.template` exists with `<resolved-by-ci>` markers | ✅ |
| `scripts/check-no-placeholder-digests.sh` exits 0 on clean file | ✅ |
| Guard wired into `.github/workflows/environment-promotion.yml` | ✅ |

### GitOps Posture

| Item | Status |
|---|---|
| ArgoCD is not installed — documented as non-operational | ✅ |
| `k8s/gitops/argocd-applications.yaml` marked with OPERATIONAL GAP comment | ✅ |
| `environment-promotion.yml` documents ArgoCD gap | ✅ |
| Deployment path: `kubectl apply` / Kustomize | ✅ |

### Secrets

| Item | Status |
|---|---|
| `VaultSourceNotSupportedError` defined and raised for `type: vault` config | ✅ |
| ESO path documented in `VaultSourceNotSupportedError` docstring | ✅ |
| Vault v1 behaviour documented in `docs/governance/compatibility-debt-registry.md` | ✅ |

### Observability

| Item | Status |
|---|---|
| LLM cost telemetry active in `governed_llm_client.py` | ✅ |
| Structured log fields: `tenant_id`, `workflow_id`, `model`, `prompt_tokens`, `completion_tokens`, `cost_usd` | ✅ |
| `monitoring/grafana/dashboards/llm-costs.json` has 7 panels (≥3 required) | ✅ |
| Harness trace event log schema contract tests pass | ✅ |
| Validation outcome log schema contract tests pass | ✅ |
| Failed/degraded workflow log schema contract tests pass | ✅ |

### database.py

| Item | Status |
|---|---|
| `get_tiered_db_session()` emits `DeprecationWarning` | ✅ |
| `get_tiered_db_session()` raises `HTTPException(422)` for unsupported tiers (not 501) | ✅ |
| No production callers of `get_tiered_db_session()` outside `database.py` | ✅ |

---

## Test Results

All 81 new tests pass across Sprint 5 and Sprint 6:

| Suite | Tests | Result |
|---|---|---|
| `tests/security/test_harness_tenant_isolation.py` | 13 | ✅ Pass |
| `tests/security/test_sprint5_smoke.py` | 15 | ✅ Pass |
| `tests/security/test_cross_stack_jwt_contract.py` | 5 | ✅ Pass |
| `tests/security/test_provider_billing_posture.py` | 14 | ✅ Pass |
| `tests/unit/test_llm_cost_log_schema.py` | 8 | ✅ Pass |
| `tests/unit/test_layer4_log_schemas.py` | 19 | ✅ Pass |
| `services/layer3-knowledge/tests/test_vault_config_source.py` | 7 | ✅ Pass |
| **Total** | **81** | **✅ All pass** |

---

## Deployment Path

**Current release path:** `kubectl apply` with Kustomize overlays.

```bash
# Render and apply a specific overlay
scripts/ci/prepare_kustomize_deploy.sh k8s/envs/staging rendered-staging.yaml
kubectl apply -f rendered-staging.yaml

# Guard against placeholder digests before apply
bash scripts/check-no-placeholder-digests.sh k8s/envs/prod/kustomization.yaml
```

**GitOps (ArgoCD):** Not operational. ArgoCD Application manifests exist in `k8s/gitops/argocd-applications.yaml` but ArgoCD is not installed. Do not claim ArgoCD reconciliation until installed.

---

## Rollback Procedure

See `docs/runbooks/deployment-rollout-and-rollback.md` for the full rollback procedure.

Summary:
1. Identify the previous stable image tag from the build metadata artifacts.
2. Update the Kustomize overlay with the previous tag.
3. Run `scripts/check-no-placeholder-digests.sh` on the overlay.
4. Apply with `kubectl apply`.
5. Verify health endpoints for all affected services.

---

## Residual Risks

| Risk | Severity | Disposition |
|---|---|---|
| `services/api` has no OIDC/PKCE | Medium | Documented; migration deferred |
| ArgoCD not installed | Low | Documented as non-operational; kubectl apply is the current path |
| Apollo/Clearbit/NewsAPI enrichment not integrated | Low | Fail-closed; mock mode requires explicit opt-in |
| Anthropic LLM adapter not implemented | Low | Raises `ProviderNotImplementedError`; no production impact |
| Grafana dashboards require live Prometheus | Low | Dashboard JSON is correct; panels render when Prometheus is available |
