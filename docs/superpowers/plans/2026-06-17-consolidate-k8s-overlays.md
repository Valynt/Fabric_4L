# Sub-plan H: Consolidate K8s Overlays/Routing/Secrets/Monitoring (#9)

**Goal:** Reduce the number of parallel Kubernetes overlay, routing, secret, and monitoring stacks to one supported path.

**Canonical path decision**
- Render stack: Kustomize (`k8s/base/` + `k8s/envs/` + `k8s/deployments/`).
- Ingress: nginx (`k8s/routing/nginx/`).
- Secrets: `k8s/external-secrets/` (or `k8s/infisical/` once migration is complete).
- Monitoring: `monitoring/`.

**Files to inspect / modify**
- `k8s/*.yml` (legacy flat manifests)
- `k8s/overlays/staging/`, `k8s/overlays/production/`
- `k8s/envs/`
- `k8s/deployments/`
- `k8s/routing/gateway-api/`, `k8s/routing/istio/`
- `k8s/external-secrets/`, `k8s/base/externalsecrets/`, `k8s/infisical/`
- `k8s/monitoring/`, `k8s/deployments/*/monitoring/`
- `monitoring/`
- `infra/helm/fabric-chart/`, `infra/argocd/applications/`
- `scripts/deploy-production.sh`, `docs/operations/RELEASE_RUNBOOK.md`

**Approach**
1. Deprecate `k8s/overlays/` and flat `k8s/*.yml`; delete after updating references.
2. Remove experimental gateway-api and istio routing stacks (or move to an `experimental/` folder outside the supported path).
3. Consolidate ExternalSecrets into the canonical directory; delete deprecated Vault-backed path.
4. Deduplicate monitoring configs into `monitoring/`.
5. Decide whether to keep Helm/ArgoCD or standardize on Kustomize; if Kustomize is canonical, archive the Helm chart.

**Validation**
- `kustomize build k8s/deployments/prod-nginx` succeeds.
- `make check-manifest-secret-hygiene` passes.
- `make check-k8s-image-digests` (if present) passes.
- No duplicate byte-for-byte manifests remain between `k8s/monitoring/` and `k8s/deployments/*/monitoring/`.

**Rollback**
Keep deleted manifests in an archive branch for one release.

**Risks**
- Production deploy scripts may reference deprecated paths.
- Experimental routing stacks may have active evaluations; confirm before deleting.
