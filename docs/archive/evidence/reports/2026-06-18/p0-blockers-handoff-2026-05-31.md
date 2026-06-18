# P0 Blockers — Final Handoff

Date: 2026-05-31
Status: **Implementation complete. Staging/runtime validation blocked pending manual GitHub/AWS setup.**
No P0 blocker is production closed.

---

## 1. What Was Implemented

### P0-007: OpenTelemetry Instrumentation
- Static contract tests: `tests/contract/test_otel_instrumentation.py` (6 tests)
- Runtime smoke test: `tests/backend_integrated/test_otel_trace_receipt.py` (3 tests)
- CI gate added to `.github/workflows/pr-checks.yml`
- Collector YAML reviewed: OTLP receivers on 4317/4318 confirmed

### P0-010: Terraform CI Integration
- GitHub Actions workflow: `.github/workflows/terraform-cd.yml`
- TFLint config: `infra/terraform/.tflint.hcl`
- Terraform preflight script: `scripts/ci/check_terraform_preflight.py`
- Policy check scripts:
  - `scripts/ci/check_terraform_rds_backup_policy.py`
  - `scripts/ci/check_terraform_elasticache_encryption.py`
  - `scripts/ci/check_terraform_s3_encryption.py`

### P0-002: AWS-Managed Database HA
- Terraform RDS module (`infra/terraform/modules/rds/`) — complete with Multi-AZ, encryption, Performance Insights
- Terraform ElastiCache module (`infra/terraform/modules/elasticache/`) — complete with failover, encryption at rest/transit
- All 3 environments (dev/staging/prod) instantiate both modules
- K8s ExternalSecrets: `k8s/external-secrets/postgres-endpoint.yaml`, `redis-endpoint.yaml`
- K8s ConfigMaps: `k8s/base/configmap-postgres.yaml`, `configmap-redis.yaml`
- Validation scripts: `validate-rds-backup.sh`, `validate-elasticache-failover.sh`
- Neo4j hosting ADR: `docs/explanations/adr/ADR-030-neo4j-hosting-decision.md`

---

## 2. What Passed Locally

| Check | Result |
|-------|--------|
| OTel static contract tests (6/6) | PASS |
| RDS backup retention policy check | PASS |
| ElastiCache encryption policy check | PASS |
| S3 encryption policy check | PASS |
| Terraform CI workflow YAML valid | PASS |
| K8s ExternalSecrets YAML valid (postgres, redis) | PASS |
| K8s ConfigMap YAML valid (postgres, redis) | PASS |
| Terraform preflight script fails correctly when config missing | PASS |
| Collector YAML has OTLP receivers and traces pipeline | PASS |

Evidence: `p0-blockers-local-evidence-2026-05-31.md`

---

## 3. What Remains Blocked

| P0 Blocker | Status | Blocker Reason |
|------------|--------|----------------|
| P0-007 OTel | **Blocked** | Staging observability environment not confirmed (Jaeger, OTel collector, billing/L2.5/L7 services) |
| P0-010 Terraform CI | **Blocked** | AWS OIDC role ARN and region not configured in GitHub; Terraform backend not initialized |
| P0-002 AWS DB HA | **Blocked** | AWS/staging environment not provisioned; RDS and ElastiCache not deployed; EKS workloads not connected |

All three share a common dependency: the staging AWS account and EKS cluster must exist and be wired to GitHub Actions.

---

## 4. Manual Steps Required

Complete `docs/runbooks/p0-aws-github-environment-setup.md` in order:

1. **GitHub repository configuration**
   - Add `AWS_TERRAFORM_ROLE_ARN` as a repository secret
   - Add `AWS_REGION` as a repository variable
   - Create `dev`, `staging`, `prod` environments; add approval rules for staging and prod

2. **AWS OIDC role setup**
   - Create OIDC identity provider for GitHub Actions
   - Create IAM role with trust policy restricting to this repository/branch
   - Attach plan-only permissions; keep apply permissions separate

3. **Terraform backend setup**
   - Create S3 buckets (`fabric-terraform-state-dev/staging/prod`) with versioning and encryption
   - Create DynamoDB lock tables (`fabric-terraform-locks-dev/staging/prod`)
   - Grant the Terraform IAM role least-privilege access to buckets and tables

4. **Trigger Terraform workflow**
   - Push a change to `infra/terraform/**` or run workflow manually
   - Verify `terraform-preflight` passes (confirms secrets are configured)
   - Verify `terraform-plan` for staging uploads an artifact
   - Review staging plan artifact for correctness
   - **Do not apply to production yet.**

5. **Staging runtime environment**
   - Confirm EKS cluster `fabric-staging` exists
   - Confirm ExternalSecrets controller installed and secret backend reachable
   - Deploy OTel collector and Jaeger
   - Deploy billing, L2.5-signal-refinery, L7-billing
   - Confirm RDS and ElastiCache endpoints are reachable from EKS nodes

---

## 5. Exact First Action After Manual Setup

After completing the runbook Sections 1–4:

1. Trigger the Terraform CI workflow via GitHub Actions.
2. Confirm the `terraform-preflight` job passes.
3. Download the `tfplan-staging` artifact.
4. Review the staging plan for:
   - `aws_db_instance` or `aws_rds_cluster` with `multi_az = true`, `storage_encrypted = true`
   - `aws_elasticache_replication_group` with `automatic_failover_enabled = true`, encryption enabled
   - No unexpected destructive changes
5. Apply the plan to staging (manual or gated action, not automated).
6. Apply K8s ExternalSecrets and ConfigMaps to staging.
7. Verify application pods can connect to PostgreSQL and Redis.
8. Run the three P0 validation scripts:
   ```bash
   ./scripts/ci/validate-rds-backup.sh fabric-staging
   ./scripts/ci/validate-elasticache-failover.sh fabric-staging
   pytest tests/backend_integrated/test_otel_trace_receipt.py -m backend_integrated
   ```
9. Capture evidence in `reports/p0-blockers-staging-evidence-YYYY-MM-DD.md`.
10. Update `docs/validation/production_readiness_execution_status.md` with results.

---

## 6. Critical Warning

**Do not mark any P0 blocker as production closed until staging evidence is captured.**

- P0-007 is **not closed** until runtime trace receipt is confirmed in staging with live services and Jaeger.
- P0-010 is **not closed** until the staging Terraform plan artifact is reviewed, OIDC assume-role succeeds, and no unexpected destructive changes exist.
- P0-002 is **not closed** until RDS backup validation, ElastiCache failover validation, and application connectivity tests all pass in staging.

Static tests and local policy checks are necessary but not sufficient for production readiness.

---

## Reference Files

| File | Purpose |
|------|---------|
| `docs/runbooks/p0-aws-github-environment-setup.md` | Operator checklist for GitHub/AWS manual setup |
| `p0-staging-environment-preflight-2026-05-31.md` | 39-item preflight checklist |
| `p0-blockers-local-evidence-2026-05-31.md` | Local verification evidence |
| `docs/validation/production_readiness_execution_status.md` | Official P0 blocker status tracking |
| `.github/workflows/terraform-cd.yml` | Terraform CI workflow |
| `tests/contract/test_otel_instrumentation.py` | Static OTel contract tests |
| `tests/backend_integrated/test_otel_trace_receipt.py` | Runtime OTel trace receipt smoke test |
