# P0 Blockers Deployment Plan

## Objective
Address the three remaining P0 blockers from the production readiness audit:
- **P0-002**: Deploy HA for databases (PostgreSQL, Redis, Neo4j)
- **P0-007**: OpenTelemetry on three remaining services (billing, L2.5-signal-refinery, L7-billing)
- **P0-010**: Terraform modules created, need CI integration

---

## 1. P0-002: High Availability (HA) Database Deployment

### Current State
- `docker-compose.ha.yml` exists with PostgreSQL primary/standby replication, PgBouncer connection pooling, and HAProxy load balancing
- K8s manifests exist for backup cronjobs (`k8s/base/postgres-backup-cronjob.yaml`, `k8s/base/neo4j-backup-cronjob.yaml`) and external secrets
- **Missing**: Kubernetes StatefulSet/Deployment manifests for running HA databases in the cluster

### Plan

#### 1.1 PostgreSQL HA (Patroni)
**Files to create:**
- `k8s/ha/postgres/patroni-statefulset.yaml` — Patroni operator-managed PostgreSQL cluster (3-node: 1 leader + 2 replicas)
- `k8s/ha/postgres/patroni-configmap.yaml` — Patroni DCS (Distributed Configuration Store) settings using Kubernetes Endpoints
- `k8s/ha/postgres/patroni-service.yaml` — Headless service for pod discovery + read/write service endpoints
- `k8s/ha/postgres/patroni-pvc.yaml` — PersistentVolumeClaims per pod (use existing storage class)
- `k8s/ha/postgres/pgbouncer-deployment.yaml` — PgBouncer connection pooler (already have secrets at `k8s/external-secrets/pgbouncer-secrets.yaml`)

**Key configurations:**
- WAL archiving to S3-compatible storage (use existing `k8s/base/postgres-backup-cronjob.yaml` pattern)
- Synchronous replication mode = `remote_apply` for strong consistency
- Automatic failover with Patroni REST API health checks
- Resource limits: 2 CPU / 4Gi memory per pod

#### 1.2 Redis Sentinel
**Files to create:**
- `k8s/ha/redis/redis-sentinel-statefulset.yaml` — 3-node Sentinel cluster (StatefulSet for stable network IDs)
- `k8s/ha/redis/redis-master-statefulset.yaml` — Redis master with AOF + RDB persistence
- `k8s/ha/redis/redis-replica-statefulset.yaml` — 2 Redis replicas for read scaling
- `k8s/ha/redis/redis-services.yaml` — Services: `redis-master` (write), `redis-replicas` (read), `redis-sentinel` (discovery)
- `k8s/ha/redis/redis-configmap.yaml` — `redis.conf` and `sentinel.conf`

**Key configurations:**
- Sentinel quorum = 2 (majority of 3)
- Down-after-milliseconds = 5000
- Parallel-syncs = 1
- Use existing `k8s/external-secrets/redis-secrets.yaml` for auth

#### 1.3 Neo4j Cluster
**Files to create:**
- `k8s/ha/neo4j/neo4j-cluster-statefulset.yaml` — 3-core Neo4j cluster (Causal Clustering)
- `k8s/ha/neo4j/neo4j-services.yaml` — Bolt (7687), HTTP (7474), intra-cluster discovery (5000)
- `k8s/ha/neo4j/neo4j-configmap.yaml` — `neo4j.conf` with `dbms.mode=CORE`, discovery endpoints
- `k8s/ha/neo4j/neo4j-pvc.yaml` — Separate PVCs for data and logs

**Key configurations:**
- ` causal_clustering.minimum_core_cluster_size_at_formation=3`
- `causal_clustering.minimum_core_cluster_size_at_runtime=3`
- Read replicas optional (add later if needed)
- Use existing `k8s/external-secrets/neo4j-secrets.yaml` for credentials

#### 1.4 Kustomization & Overlay
- `k8s/ha/kustomization.yaml` — Base kustomization including all HA components
- `k8s/overlays/prod/ha-patch.yaml` — Production-specific patches (replica counts, resource limits, affinity rules)
- `k8s/overlays/staging/ha-patch.yaml` — Staging with reduced replica counts

#### 1.5 Validation
- Add `scripts/ci/validate-ha-manifests.sh` to lint k8s manifests in CI
- Include in `make verify` gate

---

## 2. P0-007: OpenTelemetry Verification & CI Gates

### Current State
- `billing` service: Has OTel bootstrap (`init_telemetry`, `instrument_fastapi_app`) in `main.py` lines 27-58
- `layer2-5-signal-refinery`: Has `instrument_telemetry=True` in `create_fabric_app`
- `layer7-billing`: Has `instrument_telemetry=True` in `create_fabric_app`
- All other layers (L1-L6) already have OTel enabled per the codebase audit

### Plan

#### 2.1 Verify Wiring
- Confirm each service emits traces to the OpenTelemetry Collector (`k8s/monitoring/opentelemetry-collector.yaml`)
- Check OTLP endpoint configuration in each service's config/settings
- Ensure `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES`, `OTEL_EXPORTER_OTLP_ENDPOINT` env vars are set in `k8s/external-secrets/` and deployed ConfigMaps

#### 2.2 Add Regression Tests
- `tests/contract/test_otel_instrumentation.py` — Contract test that:
  - Verifies `init_telemetry` is called in billing service startup
  - Verifies `instrument_telemetry=True` is passed to `create_fabric_app` for L2.5 and L7
  - Checks that telemetry provider is not `None` at runtime
  - Fails if any new service misses OTel instrumentation

#### 2.3 CI Gate
- Add step in `.github/workflows/pr-checks.yml`:
  - Run `pytest tests/contract/test_otel_instrumentation.py`
  - Ensure OTel collector config is valid YAML (`yamllint k8s/monitoring/opentelemetry-collector.yaml`)

#### 2.4 Documentation
- Update `docs/production-readiness.md` to reflect 10/10 services instrumented

---

## 3. P0-010: Terraform CI Integration

### Current State
- `infra/terraform/modules/` — 6 modules: vpc, eks, rds, elasticache, s3, iam
- `infra/terraform/environments/` — dev, staging, prod
- `scripts/init-backend.sh` — State backend initialization
- **Missing**: GitHub Actions workflow for Terraform CI/CD

### Plan

#### 3.1 Create Workflow
**File:** `.github/workflows/terraform-cd.yml`

**Triggers:**
- `pull_request` on paths: `infra/terraform/**`
- `push` to `main` on paths: `infra/terraform/**`
- `workflow_dispatch` for manual apply

**Jobs:**
1. **terraform-fmt-validate** (all PRs):
   - `terraform fmt -check -recursive`
   - `terraform validate` per environment
   - `tflint` or `terraform-compliance` for policy checks

2. **terraform-plan** (PRs to main):
   - Run `terraform plan` for dev/staging/prod
   - Post plan output as PR comment
   - Fail on any `plan` errors

3. **terraform-apply-dev** (merge to main, auto):
   - Require `terraform-plan` success
   - Run `terraform apply -auto-approve` for dev environment

4. **terraform-apply-staging** (manual approval):
   - Require `terraform-apply-dev` success
   - Use GitHub Environments with required reviewers (1)
   - Run `terraform apply` for staging

5. **terraform-apply-prod** (manual approval):
   - Require `terraform-apply-staging` success
   - Use GitHub Environments with required reviewers (2)
   - Run `terraform apply` for prod

#### 3.2 Backend & Authentication
- Ensure `scripts/init-backend.sh` is documented in README and CI checks its idempotency
- Use OIDC federation for AWS authentication (no long-lived keys in GitHub secrets)
- Store Terraform plan artifacts between plan and apply jobs

#### 3.3 Policy & Compliance
- Add `infra/terraform/.tflint.hcl` for linting rules
- Add `infra/terraform/policy/` directory with OPA/Checkov or Sentinel policies:
  - Enforce S3 encryption
  - Enforce RDS backup retention >= 7 days in prod
  - Enforce EKS node group minimum instance type
- Run policy checks in CI before apply

#### 3.4 Documentation
- Update `infra/terraform/README.md` with CI/CD usage instructions
- Add runbook for manual Terraform operations and rollback procedures

---

## Execution Order

1. **Phase 1**: P0-007 (OTel verification + tests) — Fastest win, already partially implemented
2. **Phase 2**: P0-010 (Terraform CI workflow) — No runtime impact, builds infrastructure automation
3. **Phase 3**: P0-002 (HA k8s manifests) — Most complex, deploy to staging first, then prod

## Files to Create/Modify Summary

| File | Action | Blocker |
|------|--------|---------|
| `k8s/ha/postgres/*.yaml` | Create | P0-002 |
| `k8s/ha/redis/*.yaml` | Create | P0-002 |
| `k8s/ha/neo4j/*.yaml` | Create | P0-002 |
| `k8s/ha/kustomization.yaml` | Create | P0-002 |
| `k8s/overlays/*/ha-patch.yaml` | Create | P0-002 |
| `scripts/ci/validate-ha-manifests.sh` | Create | P0-002 |
| `tests/contract/test_otel_instrumentation.py` | Create | P0-007 |
| `.github/workflows/pr-checks.yml` | Modify | P0-007 |
| `.github/workflows/terraform-cd.yml` | Create | P0-010 |
| `infra/terraform/.tflint.hcl` | Create | P0-010 |
| `infra/terraform/policy/` | Create | P0-010 |
| `infra/terraform/README.md` | Update | P0-010 |

---

## Open Questions

1. Should HA manifests target a specific k8s distribution (EKS, GKE, on-prem)? Current Terraform targets AWS/EKS.
2. Should we use Helm charts for Patroni/Neo4j instead of raw manifests? (e.g., Zalando Patroni Helm chart)
3. Should PgBouncer run as a sidecar in application pods or as a standalone Deployment?

---

*Plan prepared for user confirmation before implementation.*
