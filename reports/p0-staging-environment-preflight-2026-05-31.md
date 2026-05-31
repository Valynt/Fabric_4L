# P0 Staging Environment Preflight Checklist

Date: 2026-05-31
Status: **BLOCKED — Staging/AWS environment prerequisites not yet confirmed**
Purpose: Enumerate every prerequisite required before P0-002, P0-007, and P0-010 runtime validation can proceed.

---

## GitHub Actions / Terraform CI Prerequisites

| # | Check | Status | Evidence / Notes |
|---|-------|--------|------------------|
| 1 | Terraform CI workflow exists (`.github/workflows/terraform-cd.yml`) | PASS | File present, YAML valid |
| 2 | GitHub repository has OIDC provider configured with AWS | **BLOCKED** | Requires `AWS_TERRAFORM_ROLE_ARN` secret |
| 3 | `AWS_TERRAFORM_ROLE_ARN` repository secret configured | **BLOCKED** | Not yet confirmed |
| 4 | `AWS_REGION` repository variable configured | **BLOCKED** | Not yet confirmed |
| 5 | GitHub environment `staging` exists with required reviewer rules | **BLOCKED** | Not yet confirmed |
| 6 | Terraform backend S3 bucket `fabric-terraform-state-staging` exists | **BLOCKED** | Must exist before `terraform init` |
| 7 | Terraform backend DynamoDB lock table `fabric-terraform-locks-staging` exists | **BLOCKED** | Must exist before `terraform init` |
| 8 | `terraform plan` for staging runs successfully in GitHub Actions | **BLOCKED** | Depends on items 2–7 |
| 9 | Plan artifact uploaded and reviewable | **BLOCKED** | Depends on item 8 |

### Required Inputs (Placeholder / TBD)

```yaml
# These must be configured in GitHub repository settings before P0-010 can close
secrets.AWS_TERRAFORM_ROLE_ARN: "arn:aws:iam::<account>:role/<role-name>"  # TBD
vars.AWS_REGION: "us-east-1"  # TBD — must match backend config in main.tf
```

---

## Staging EKS Cluster Prerequisites

| # | Check | Status | Evidence / Notes |
|---|-------|--------|------------------|
| 10 | Staging EKS cluster `fabric-staging` exists | **BLOCKED** | Not yet confirmed |
| 11 | kubectl context for staging is available locally or via CI | **BLOCKED** | Not yet confirmed |
| 12 | EKS worker nodes can reach AWS VPC endpoints (STS, EC2, etc.) | **BLOCKED** | Required for OIDC/IRSA |
| 13 | VPC with database subnets exists (`10.1.201.0/24`, `10.1.202.0/24`, `10.1.203.0/24`) | **BLOCKED** | Defined in `infra/terraform/environments/staging/main.tf` |

---

## OpenTelemetry / Observability Prerequisites

| # | Check | Status | Evidence / Notes |
|---|-------|--------|------------------|
| 14 | OpenTelemetry Collector deployed in staging | **BLOCKED** | Requires `k8s/monitoring/opentelemetry-collector.yaml` applied |
| 15 | Jaeger (or equivalent trace backend) deployed and reachable | **BLOCKED** | Required for trace receipt validation |
| 16 | Jaeger query API endpoint known and accessible | **BLOCKED** | Required for `test_otel_trace_receipt.py` |
| 17 | OTel collector can reach Jaeger exporter endpoint | **BLOCKED** | Collector config must be verified post-deployment |

---

## Application Service Prerequisites

| # | Check | Status | Evidence / Notes |
|---|-------|--------|------------------|
| 18 | Billing service deployed and healthy in staging | **BLOCKED** | Required for OTel trace receipt |
| 19 | Layer 2.5-signal-refinery deployed and healthy in staging | **BLOCKED** | Required for OTel trace receipt |
| 20 | Layer 7-billing deployed and healthy in staging | **BLOCKED** | Required for OTel trace receipt |
| 21 | Services configured with `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` | **BLOCKED** | Environment variables must be set in deployment manifests |

---

## Database / Cache Prerequisites

| # | Check | Status | Evidence / Notes |
|---|-------|--------|------------------|
| 22 | RDS/Aurora staging instance/cluster provisioned | **BLOCKED** | Requires Terraform apply in staging |
| 23 | RDS endpoint known and reachable from EKS worker node SG | **BLOCKED** | Security group rules must allow EKS → RDS |
| 24 | ElastiCache/Valkey staging replication group provisioned | **BLOCKED** | Requires Terraform apply in staging |
| 25 | ElastiCache primary endpoint known and reachable from EKS worker node SG | **BLOCKED** | Security group rules must allow EKS → ElastiCache |
| 26 | ExternalSecrets controller installed in staging cluster | **BLOCKED** | Required for `postgres-endpoint.yaml` and `redis-endpoint.yaml` |
| 27 | Vault or secret backend reachable from ExternalSecrets controller | **BLOCKED** | Required for secret syncing |
| 28 | `postgres-endpoint` ExternalSecret resolves and creates K8s Secret | **BLOCKED** | Requires items 22, 26, 27 |
| 29 | `redis-endpoint` ExternalSecret resolves and creates K8s Secret | **BLOCKED** | Requires items 24, 26, 27 |
| 30 | Application pods can connect to PostgreSQL via ExternalSecret | **BLOCKED** | Requires items 22, 28 |
| 31 | Application pods can connect to Redis via ExternalSecret | **BLOCKED** | Requires items 24, 29 |
| 32 | RDS backup retention >= 3 days (staging) | **BLOCKED** | Requires item 22; validate with `validate-rds-backup.sh` |
| 33 | ElastiCache automatic failover enabled | **BLOCKED** | Requires item 24; validate with `validate-elasticache-failover.sh` |

---

## Script / Tool Prerequisites

| # | Check | Status | Evidence / Notes |
|---|-------|--------|------------------|
| 34 | `scripts/ci/validate-rds-backup.sh` executable | PASS | File present, syntax valid |
| 35 | `scripts/ci/validate-elasticache-failover.sh` executable | PASS | File present, syntax valid |
| 36 | `tests/backend_integrated/test_otel_trace_receipt.py` present and runnable | PASS | File present, syntax valid |
| 37 | `aws` CLI available in execution environment | **BLOCKED** | Not installed locally; must be available in GitHub Actions or WSL |
| 38 | `terraform` CLI available in execution environment | **BLOCKED** | Not installed locally; must be available in GitHub Actions |
| 39 | `kubectl` available in execution environment | PASS | v1.34.1 available locally |

---

## Preflight Pass Criteria

Before any P0 blocker can move from "blocked pending environment" to "staging validation in progress", the following must all be true:

- [ ] `AWS_TERRAFORM_ROLE_ARN` and `AWS_REGION` configured in GitHub
- [ ] Terraform backend bucket and lock table exist
- [ ] GitHub Actions `terraform plan` for staging succeeds and uploads artifact
- [ ] Staging EKS cluster exists and kubectl context works
- [ ] RDS/Aurora and ElastiCache staging resources exist (via Terraform apply)
- [ ] ExternalSecrets controller installed and syncing secrets
- [ ] OTel collector and Jaeger deployed and reachable
- [ ] Billing, L2.5, and L7 services deployed and healthy
- [ ] `aws` and `terraform` CLIs available in the execution environment

---

## Next Actions

1. **Configure GitHub repository secrets/variables:**
   - Add `AWS_TERRAFORM_ROLE_ARN` to repository secrets
   - Add `AWS_REGION` to repository variables
   - Create GitHub `staging` environment with required reviewers

2. **Initialize Terraform backend:**
   - Create S3 bucket `fabric-terraform-state-staging`
   - Create DynamoDB table `fabric-terraform-locks-staging`

3. **Trigger Terraform plan via GitHub Actions:**
   - Validate OIDC assume-role succeeds
   - Review staging plan artifact for correctness
   - Apply to staging after review

4. **Confirm staging EKS cluster:**
   - Verify cluster exists and nodes are Ready
   - Verify kubectl context works

5. **Deploy observability stack:**
   - Apply `k8s/monitoring/opentelemetry-collector.yaml`
   - Deploy Jaeger query + collector

6. **Deploy application services:**
   - Deploy billing, L2.5-signal-refinery, L7-billing to staging
   - Verify health endpoints respond

7. **Apply ExternalSecrets and ConfigMaps:**
   - Apply `k8s/external-secrets/postgres-endpoint.yaml`
   - Apply `k8s/external-secrets/redis-endpoint.yaml`
   - Apply `k8s/base/configmap-postgres.yaml`
   - Apply `k8s/base/configmap-redis.yaml`

8. **Run validation scripts:**
   - `validate-rds-backup.sh fabric-staging`
   - `validate-elasticache-failover.sh fabric-staging`
   - `pytest tests/backend_integrated/test_otel_trace_receipt.py -m backend_integrated`

---

*This preflight checklist is a living document. Items should be checked off as the staging environment is provisioned and confirmed.*
