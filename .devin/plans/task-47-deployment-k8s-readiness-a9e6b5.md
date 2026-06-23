# Task 47 — Deployment/K8s Readiness Plan

This plan closes launch-blocking Kubernetes deployment gaps by introducing a production-ready Kustomize structure, enforcing fail-loud CI validation (including mandatory server-side dry-run on `kind`), and migrating services incrementally with preserved rollback safety and runtime verification evidence.

## Scope and Outcomes

- Include backend layers L1-L6 and frontend deployment manifests.
- Introduce `k8s/base/` plus `k8s/overlays/dev/` and `k8s/overlays/prod/`.
- Preserve existing flat manifests during migration to avoid big-bang replacement.
- Enforce production image strategy (no `:latest` in prod overlays).
- Add CI gates with fast static checks and required server-side dry-run on ephemeral `kind` cluster.

## Guiding Constraints

- Rollout is incremental: structure + validation first, then service-by-service migration.
- Existing working manifests remain available until each migrated component is verified.
- CI must fail loudly: no fallback substitution if `kind` bootstrap or server dry-run fails.
- Acceptance requires both static evidence and runtime evidence.

## Implementation Phases

### Phase 1: Foundation (Structure + Validation First)

1. Create Kustomize directories and scaffolding:
   - `k8s/base/`
   - `k8s/overlays/dev/`
   - `k8s/overlays/prod/`
2. Add base resources for:
   - Namespace, shared ConfigMap, secrets templates, infra (Postgres/Redis/Neo4j), L1-L6, frontend.
3. Add overlays:
   - `dev`: compatibility defaults, local/dev image tags, pragmatic resource settings.
   - `prod`: registry/tag pinning, stricter readiness defaults, no `:latest`.
4. Keep legacy flat manifests untouched but document migration status mapping from flat → kustomize resources.

### Phase 2: Consistency Hardening (Manifest + Config Alignment)

1. Normalize labels/selectors/ports/probes naming conventions across all services.
2. Reconcile inter-service URL/config key consistency (ConfigMap keys and app env expectations).
3. Ensure secrets references are explicit and production-safe (template + external-secrets path).
4. Add frontend service/deployment ingress-compatible manifest set (or service exposure pattern already used in repo).
5. Ensure probe paths/ports align with actual app health endpoints per layer.

### Phase 3: CI Deployment Gates (Fail Loudly)

1. Add fast pre-check job(s):
   - `kustomize build` for each overlay
   - schema validation (`kubeconform`)
   - optional `kubectl --dry-run=client` sanity check
2. Add required server-side gate job:
   - create ephemeral `kind` cluster
   - apply CRD-safe prerequisites if needed
   - run `kubectl apply --dry-run=server -k k8s/overlays/dev`
   - run `kubectl apply --dry-run=server -k k8s/overlays/prod`
3. Mark bootstrap failures as hard failures (no downgrade/fallback).
4. Wire jobs into PR-required checks path (and main branch protection-compatible workflow).

### Phase 4: Incremental Migration and Runtime Proof

1. Migrate and validate in dependency-aware order:
   - infra → L1-L4 → L5-L6 → frontend.
2. For each step:
   - kustomize render diff review
   - server-side dry-run pass
   - targeted runtime check evidence (pods ready + health endpoints).
3. Update `k8s/README.md` with canonical Kustomize deployment paths and verification commands.
4. Keep rollback path explicit (ability to deploy previous stable flat manifests during transition).

## Evidence and Acceptance Criteria

Task is complete only when all of the following are met:

1. **Kustomize structure exists and is canonical**
   - `k8s/base/`, `k8s/overlays/dev/`, `k8s/overlays/prod/` checked in and used by docs/CI.
2. **Frontend included**
   - frontend deployment/service manifests included in base + overlays.
3. **Config/secrets/manifests consistent**
   - services, ConfigMaps, and secrets templates align with runtime env contracts.
4. **Production image policy enforced**
   - prod overlay uses pinned registry/tag references; no `:latest` in prod path.
5. **CI gates are enforced and fail loud**
   - static pre-checks pass and required `kind` + server dry-run gates pass.
   - any cluster bootstrap or server validation failure fails the workflow.
6. **Runtime evidence captured**
   - deployment verification output for all in-scope services (L1-L6 + frontend), including readiness and health checks.

## Deliverables

- Kustomize manifests and overlays under `k8s/`.
- Frontend K8s deployment resources.
- Updated CI workflow(s) for pre-check + mandatory server-side dry-run.
- Updated deployment documentation and migration/runbook notes.
- Task 47 evidence summary artifact (static + runtime proof checklist).
