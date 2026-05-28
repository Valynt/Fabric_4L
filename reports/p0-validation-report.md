# P0 Environment Packaging / Security PR Batch — Validation Report

## Summary

Code-complete accepted. This report documents the focused validation pass run before marking the batch merge-ready.

---

## Validation 1: Kustomize Render Checks

**Status**: File-verified (kustomize not available locally)

### k8s/envs/staging
- **namespace**: `value-fabric-staging` ✅
- **ExternalSecret patches**: All ExternalSecrets patched to render in `value-fabric-staging` ✅
- **resources**: `../../base`, `../../external-secrets/vault-integration.yml`, `../../external-secrets/vault-database-dynamic.yml`, `../../external-secrets/redis-secrets.yaml`, `../../monitoring/placeholder-secret-scanner-cronjob.yaml` ✅
- **images**: Service images use comment-only digest entries (injected by `prepare_kustomize_deploy.sh` at deploy time). Infrastructure images use explicit versions (`postgres:15.10-alpine`, `redis:7.4-alpine`, `neo4j:5.25-community`) — these are not mutable tags like `:latest`. ✅
- **No hardcoded production namespace DNS** in resources included in this overlay. ✅

### k8s/overlays/staging
- **namespace**: `value-fabric-staging` ✅
- **ExternalSecret patches**: All ExternalSecrets patched to render in `value-fabric-staging` ✅
- **images**: Uses immutable `sha-<commit>` tags (e.g., `sha-e2a0c3eac82766f79f3b3daac750114b571fdb6a`). Not a mutable tag pattern. ✅

### k8s/envs/prod
- **namespace**: `value-fabric` ✅
- **resources**: Includes `../../routing/gateway-api` and `hostname-config.yaml` for Gateway API/TLS integration. ✅
- **replacements**: ConfigMap `routing-host` fields (`host`, `apiHost`) inject into Gateway listeners, HTTPRoute hostnames, and Certificate dnsNames. ✅
- **images**: Comment-only digest entries (injected at deploy time). No mutable tags committed. ✅

### k8s/overlays/production
- **namespace**: `fabric-4l-prod` ✅
- **images**: Comment-only digest entries. No mutable tags committed. ✅

**Fix applied during validation**: Removed fake `sha256:a1b2c3d4...` digest placeholders from `k8s/envs/staging/kustomization.yaml`. Replaced with comment-only entries matching prod overlay style.

---

## Validation 2: New Validation Scripts

**Status**: One script verified locally; others require kustomize (documented as CI-blocked)

### scripts/ci/validate-deploy-safety.sh
- **Result**: ✅ PASS (verified locally)
- Checks deploy workflow kubeconfig step exits with error (fail-closed)
- Checks rollback job kubeconfig step also exits with error
- Checks cluster context confirmation step exists
- Checks deploy workflow rejects mutable image refs
- Checks rollback job exists

### scripts/ci/validate-staging-namespace.sh
- **Result**: Requires kustomize (not available locally) — will run in CI
- Logic verified by file inspection

### scripts/ci/validate-staging-dns.sh
- **Result**: Requires kustomize (not available locally) — will run in CI
- Logic verified by file inspection

### scripts/ci/validate-redis-auth.sh
- **Result**: Requires kustomize (not available locally) — will run in CI
- Logic verified by file inspection

### scripts/ci/validate-k8s-image-tags.sh
- **Result**: Requires kustomize + yq (not available locally) — will run in CI
- Logic verified by file inspection. Script checks:
  - Rendered manifest images for `:latest`, branch names, semver tags
  - kustomization.yaml `newTag:` values for same patterns
  - Does NOT check `k8s/base/` (dev manifests allowed to use mutable tags)
  - `sha-<commit>` tags are allowed (immutable)

### scripts/ci/validate-gateway-api.sh
- **Result**: Requires kustomize + yq (not available locally) — will run in CI
- Logic verified by file inspection

---

## Validation 3: Redis Auth Compatibility

**Status**: ✅ All K8s base deployments updated; docker-compose dev/live already authenticated; test compose files documented

### Changes made during validation

1. **Base K8s deployments** updated to reference `redis-secret` for `REDIS_URL`:
   - `k8s/base/layer1-ingestion.yml` (2 occurrences — main + worker) ✅
   - `k8s/base/layer2-extraction.yml` ✅
   - `k8s/base/layer3-knowledge.yml` ✅
   - `k8s/base/layer1-celery.yaml` (3 occurrences — worker, beat, flower) ✅
   - `k8s/base/configmap-global.yml` — removed hardcoded `REDIS_URL` ✅

2. **Root K8s manifests** updated to reference `redis-secret`:
   - `k8s/layer1-ingestion.yml` (2 occurrences) ✅
   - `k8s/layer2-extraction.yml` ✅
   - `k8s/layer3-knowledge.yml` ✅
   - `k8s/layer4-agents.yml` ✅
   - `k8s/configmap-global.yml` — removed hardcoded `REDIS_URL` ✅

3. **ExternalSecret defaults** updated to use `rediss://` (TLS) instead of plain `redis://`:
   - `k8s/external-secrets/layer1-secrets.yaml` ✅
   - `k8s/external-secrets/layer2-secrets.yaml` ✅
   - `k8s/external-secrets/layer3-secrets.yaml` ✅
   - `layer4-secrets.yaml` already had `rediss://redis:6379` ✅

### Verified: no `redis://redis:6379/0` remains in any K8s manifest

### Docker Compose status
- `docker-compose.yml` (live stack): Redis uses `--requirepass ${REDIS_PASSWORD}`; services use authenticated URLs ✅
- `docker-compose.dev.yml`: Redis uses `--requirepass ${REDIS_PASSWORD}`; services use `redis://:${REDIS_PASSWORD}@redis:6379/0` ✅
- `docker-compose.backend-integrated.yml`: Unauthenticated Redis (dev/test environment) — **documented as intentional dev difference** ⚠️
- `docker-compose.e2e.yml`: Unauthenticated Redis (test environment) — **documented as intentional dev difference** ⚠️
- `docker-compose.release-smoke.yml`: Unauthenticated Redis (test environment) — **documented as intentional dev difference** ⚠️

### Celery/Broker/Backend
- `layer1-celery.yaml` already used `layer1-secrets` for `REDIS_URL`; updated to use `redis-secret` ✅
- Docker-compose dev sets `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` with `${REDIS_PASSWORD}` ✅

---

## Validation 4: Image Digest Workflow

**Status**: ✅ Verified by file inspection

### Production overlays
- `k8s/envs/prod/kustomization.yaml`: No mutable tags committed. Service images use comment-only entries. Infrastructure uses explicit versions (`15.10-alpine`, `7.4-alpine`, `5.25-community`). ✅
- `k8s/overlays/production/kustomization.yaml`: No mutable tags committed. Same comment-only approach. ✅

### Staging overlays
- `k8s/envs/staging/kustomization.yaml`: Comment-only entries. No fake digests. ✅
- `k8s/overlays/staging/kustomization.yaml`: Uses `sha-e2a0c3eac82766f79f3b3daac750114b571fdb6a` tags. These are immutable commit-SHA tags, not mutable branch tags. ✅

### Base manifests
- `k8s/base/kustomization.yaml` still uses `newTag: main` for dev convenience. This is fine — validation scripts do NOT check `k8s/base/`. ✅

### Deploy workflow
- `.github/workflows/deploy.yml` calls `prepare_kustomize_deploy.sh` to resolve mutable tags to SHA256 digests before applying. ✅
- The script uses `docker buildx imagetools inspect` to get real digests, then `kustomize edit set image` to inject them. ✅
- Post-injection checks verify no mutable tags remain in rendered output. ✅

---

## Validation 5: Gateway API / TLS

**Status**: ✅ Verified by file inspection

### Gateway API integration
- `k8s/envs/prod/kustomization.yaml` includes `../../routing/gateway-api` and `hostname-config.yaml` ✅
- `k8s/envs/prod/hostname-config.yaml` defines `host: www.valuepact.ai` and `apiHost: api.valuepact.ai` ✅
- Kustomize `replacements:` inject hostnames into:
  - Gateway listeners (4 listeners: http-frontend, https-frontend, http-api, https-api) ✅
  - HTTPRoute hostnames (`frontend`, `layer-apis`) ✅
  - Certificate dnsNames (`frontend-tls`, `layer-apis-tls`) ✅

### Routing exclusivity
- **No overlay includes both Gateway API and nginx/istio routing simultaneously.**
- `k8s/envs/prod` includes only `../../routing/gateway-api`
- `k8s/routing/nginx/` and `k8s/routing/istio/` exist as alternatives but are NOT referenced by any overlay kustomization.
- `k8s/deployments/prod-gateway-api/` exists as a separate deployment target for Gateway API.

### TLS expectations
- Gateway API resources reference `cert-manager.io/cluster-issuer: letsencrypt-prod`
- Certificates use `letsencrypt-prod` ClusterIssuer
- Requires cert-manager with Gateway API support (v1.13+ with `--feature-gates=ExperimentalGatewayAPISupport=true`)

---

## Validation 6: Deploy Safety Guardrails

**Status**: ✅ Verified locally

### Fail-closed kubeconfig
- Deploy workflow `Configure kubeconfig` step prints `::error::` and calls `exit 1` ✅
- Rollback job `Configure kubeconfig` step also prints `::error::` and calls `exit 1` ✅
- Both steps include documented cloud-provider examples (AWS EKS, GKE, AKS) ✅

### Cluster context sanity checks
- Added `Confirm cluster context and namespace` step that:
  - Reads current kubectl context
  - Reads expected namespace from overlay
  - Fails if context contains `"prod"` but environment is not `production` ✅

### No silent defaults
- No step falls back to a default cluster/context/namespace ✅
- Rollback job re-derives namespace from overlay (not from env var) ✅

---

## Validation 7: CI Integration

**Status**: ✅ Verified by file inspection

### `.github/workflows/pr-checks.yml` — `structural-preflight` job

All five validation scripts are wired in sequence:

1. `validate-staging-namespace.sh` (staging env + staging overlay) ✅
2. `validate-staging-dns.sh` (staging env + staging overlay) ✅
3. `validate-redis-auth.sh` (prod env + staging env) ✅
4. `validate-k8s-image-tags.sh` (prod env + staging env + production overlay + staging overlay) ✅
5. `validate-gateway-api.sh` (prod env) ✅
6. `validate-deploy-safety.sh` (no args — checks deploy.yml directly) ✅

Each script runs with `bash` and will fail the `structural-preflight` job on nonzero exit. ✅

---

## Fixes Applied During Validation

1. **Removed fake digest placeholders** from `k8s/envs/staging/kustomization.yaml` (replaced with comment-only entries)
2. **Updated base K8s deployments** to use `redis-secret` instead of hardcoded unauthenticated `redis://redis:6379/0`
3. **Updated root K8s manifests** to use `redis-secret` for consistency
4. **Removed REDIS_URL from base ConfigMap** (`k8s/base/configmap-global.yml` and `k8s/configmap-global.yml`)
5. **Updated ExternalSecret Redis defaults** from `redis://redis:6379` to `rediss://redis:6379/0` (TLS, still no auth but fails closed against password-protected Redis)
6. **Fixed `validate-deploy-safety.sh`** grep pattern to avoid false negative on rollback kubeconfig check

---

## Could Not Be Verified Locally

- `kustomize build` for all four overlays (kustomize not installed on this machine)
- `validate-staging-namespace.sh`, `validate-staging-dns.sh`, `validate-redis-auth.sh`, `validate-k8s-image-tags.sh`, `validate-gateway-api.sh` — all require kustomize (and some require yq)
- These will run in CI under the `structural-preflight` job

---

## Decision

**Code-complete accepted. Merge after CI `structural-preflight` passes.**

All intentional dev/prod differences are documented:
- Dev/test docker-compose files use unauthenticated Redis (dev convenience)
- Base kustomization uses `newTag: main` for local dev (overridden by overlays for staging/prod)
- Production image digests are injected at deploy time, not committed to overlays
