# P0 Operator Runbook: GitHub / AWS Environment Setup

## Purpose

Operate this procedure safely while preserving tenant isolation, evidence, reversibility, and the existing service contract.

## Trigger

A production/staging environment is created, recovered, or found missing required GitHub/AWS/OIDC configuration.

## Severity

SEV1 when production controls or credentials are exposed; SEV2 when deployment is blocked or trust is broken; SEV3 for non-production setup drift.

## Preconditions

- Confirm the incident/request owner, affected environment, authorized tenant scope, and required approvals.
- Verify access to the relevant dashboards, audit records, secrets, backups, and deployment metadata.
- Capture the current version and state before making changes; destructive operations require explicit approval.

## Immediate Actions

1. Stop or freeze the smallest unsafe scope and declare the severity.
2. Preserve logs, traces, audit records, identifiers, configuration, and timestamps before mutation or restart.
3. Notify the owning on-call and Security when authorization, privacy, or tenant isolation may be affected.

## Diagnosis Steps

1. Confirm the trigger, timeline, affected tenants/customers, and last known-good state.
2. Correlate alerts, logs, traces, audit events, recent deployments, configuration changes, and dependency health.
3. Test whether impact is tenant-specific, regional, provider-specific, deployment-specific, or global.

## Resolution Steps

1. Apply the least-risk reversible correction described in the procedure details below.
2. Preserve fail-closed controls, tenant scope, contract compatibility, and auditability.
3. Record commands, approvals, state transitions, and the reason for the selected resolution.

## Validation

- Re-run the related gates and targeted service checks.
- Validate the affected customer path and a known-unaffected control tenant where tenant data is involved.
- Confirm alerts clear, audit evidence is complete, and no new errors or cross-tenant results appear.

## Rollback / Fallback

Return to the captured last known-good deployment, configuration, routing, or data artifact if validation fails. Keep the affected capability contained when no safe fallback preserves security and tenant isolation.

## Customer / Stakeholder Communication

Use the declared severity cadence. Report confirmed scope, customer impact, mitigation, residual risk, and next update time; never include secrets, raw customer data, or another tenant's identifiers.

## Evidence to Preserve

Preserve alert and dashboard snapshots, UTC timestamps, affected tenant/customer IDs, deployment SHAs, sanitized logs/traces, audit events, approvals, commands, gate outputs, and validation results in the incident or request record.

## Related Gates

- Terraform plan/apply deployment gates; GitHub environment protection checks; Infisical OIDC fail-closed checks; `make production-readiness-gate`.

## Related Runbooks

- ./deployment/deploy-production-release.md, ./operational/ci-infisical-oidc-recovery.md, ./security/respond-to-secret-leak.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

This runbook contains the manual steps required to configure the GitHub repository and AWS account so that P0-002, P0-007, and P0-010 runtime validation can proceed. It does **not** cover application code changes, secret-backend administration, or cluster application deployment — those are tracked separately.

**Prerequisites:**
- AWS account with IAM administrative access
- GitHub repository administrative access
- Terraform CLI installed locally (for backend bootstrap only)

**Out of scope:**
- Vault / Infisical / secret-backend setup — see `AGENTS.md` and the platform team's secret-management runbooks
- EKS application deployment — see service-specific deployment runbooks
- Neo4j hosting decision — see `docs/explanations/adr/ADR-030-neo4j-hosting-decision.md`

---

### 1. GitHub Repository Configuration

#### 1.1 Required Repository Secret

Navigate to **Settings -> Secrets and variables -> Actions -> New repository secret**.

| Secret Name | Description | Example Placeholder |
|-------------|-------------|---------------------|
| `AWS_TERRAFORM_ROLE_ARN` | IAM role ARN that GitHub Actions assumes via OIDC | `<PLACEHOLDER: arn:aws:iam::<account>:role/<role-name>>` |

> **Do not use real account IDs or fake secrets in the repo.** Configure this only in the GitHub web UI.

#### 1.2 Required Repository Variable

Navigate to **Settings -> Secrets and variables -> Actions -> Variables -> New repository variable**.

| Variable Name | Description | Example |
|---------------|-------------|---------|
| `AWS_REGION` | AWS region for Terraform operations | `us-east-1` |

#### 1.3 GitHub Environments

Navigate to **Settings -> Environments** and create or verify:

| Environment | Purpose | Protection Rules |
|-------------|---------|----------------|
| `dev` | Development Terraform workspace | Optional: none or basic branch restriction |
| `staging` | Staging Terraform workspace | **Required:** manual approval from at least one platform operator |
| `prod` | Production Terraform workspace | **Required:** manual approval from at least two platform operators; optionally restrict to `main` branch |

> **Note:** The Terraform CI workflow (`.github/workflows/terraform-cd.yml`) uses `vars.AWS_REGION` and `secrets.AWS_TERRAFORM_ROLE_ARN`. The `plan` job runs on pull requests; `apply` is gated and not enabled in this workflow yet.

---

### 2. AWS OIDC Role Setup

#### 2.1 Create the OIDC Identity Provider (if not already present)

In the AWS account, create an IAM OIDC identity provider for GitHub Actions:

- **Provider URL:** `https://token.actions.githubusercontent.com`
- **Audience (client ID):** `sts.amazonaws.com`
- **Thumbprint:** Use the latest GitHub OIDC thumbprint (AWS console will auto-fill this as of 2023)

#### 2.2 Create the IAM Role for Terraform

Create an IAM role named `<PLACEHOLDER: FabricTerraformRole>` (or your preferred name) with the following trust policy.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<PLACEHOLDER: account-id>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<PLACEHOLDER: org/Fabric_4L>:ref:refs/heads/*"
        },
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

**Restrict by branch or environment (recommended):**

For stricter security, replace the `StringLike` condition with one of the following:

- Restrict to `main` branch only:
  ```json
  "token.actions.githubusercontent.com:sub": "repo:<PLACEHOLDER: org/Fabric_4L>:ref:refs/heads/main"
  ```
- Restrict to specific environments (requires GitHub Environments):
  ```json
  "token.actions.githubusercontent.com:sub": "repo:<PLACEHOLDER: org/Fabric_4L>:environment:staging"
  ```

#### 2.3 Role Permissions: Plan vs Apply

#### Plan-Only Permissions (Minimum)

Attach a policy that allows read-only and planning operations:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformPlan",
      "Effect": "Allow",
      "Action": [
        "ec2:Describe*",
        "rds:Describe*",
        "elasticache:Describe*",
        "s3:GetObject",
        "s3:ListBucket",
        "iam:GetRole",
        "iam:GetPolicy",
        "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies",
        "dynamodb:GetItem",
        "eks:Describe*"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Apply permissions should be more restricted than plan permissions.** If you intend to allow `terraform apply` from CI in the future, create a second role or add a conditional policy that requires additional approval steps or environment gates. Do not grant full write access for plan-only workflows.

#### Apply Permissions (Future / Separate Role)

When enabling apply in CI, create a separate role or add write permissions scoped to the specific resources Terraform manages:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformApplyRestricted",
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "rds:*",
        "elasticache:*",
        "s3:*",
        "iam:*",
        "dynamodb:*",
        "eks:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "<PLACEHOLDER: us-east-1>"
        }
      }
    }
  ]
}
```

> **Recommendation:** Start with the plan-only role. Upgrade to the apply role only after the staging plan has been reviewed and approved manually.

---

### 3. Terraform Backend Setup

Terraform state is stored in S3 with DynamoDB locking. These resources must exist before the GitHub Actions workflow can run `terraform init` with a backend.

#### 3.1 Required Resources

| Resource | Dev | Staging | Prod |
|----------|-----|---------|------|
| S3 bucket for state | `fabric-terraform-state-dev` | `fabric-terraform-state-staging` | `fabric-terraform-state-prod` |
| DynamoDB lock table | `fabric-terraform-locks-dev` | `fabric-terraform-locks-staging` | `fabric-terraform-locks-prod` |

> Bucket names are already configured in `infra/terraform/environments/*/main.tf`.

#### 3.2 Create S3 Buckets (one per environment)

Example for staging (repeat for dev and prod):

```bash
# Example — replace <account-id> and region as needed
aws s3api create-bucket \
  --bucket fabric-terraform-state-staging \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket fabric-terraform-state-staging \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket fabric-terraform-state-staging \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      },
      "BucketKeyEnabled": true
    }]
  }'
```

#### 3.3 Create DynamoDB Lock Tables (one per environment)

```bash
# Example — staging
aws dynamodb create-table \
  --table-name fabric-terraform-locks-staging \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

#### 3.4 Least-Privilege Access

The Terraform IAM role (from Section 2) needs the following S3 and DynamoDB permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TerraformStateBackend",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::fabric-terraform-state-*",
        "arn:aws:s3:::fabric-terraform-state-*/*"
      ]
    },
    {
      "Sid": "TerraformStateLock",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/fabric-terraform-locks-*"
      ]
    }
  ]
}
```

---

### 4. Workflow Trigger Instructions

After completing Sections 1–3, trigger the Terraform CI workflow.

#### 4.1 How to Trigger

1. Open a PR that changes files under `infra/terraform/**` or `.github/workflows/terraform-cd.yml`
2. Or manually trigger via **Actions -> Terraform CD -> Run workflow**

#### 4.2 Expected Signals

| Job | Expected Result | Failure Signal |
|-----|---------------|----------------|
| `terraform-preflight` | Pass | Fails if `AWS_TERRAFORM_ROLE_ARN` or `AWS_REGION` missing / placeholder |
| `terraform-fmt` | Pass | Fails if Terraform files are not formatted |
| `terraform-validate` | Pass per environment | Fails if `terraform validate` returns errors |
| `terraform-lint` | Pass | Fails if `tflint` finds issues |
| `terraform-plan` | Artifact uploaded per environment | Fails if OIDC assume-role fails, or `terraform plan` errors |
| `terraform-policy-check` | Pass | Fails if Checkov or custom policy checks detect violations |

#### 4.3 Review the Staging Plan Artifact

1. Go to **Actions -> Terraform CD -> latest run**
2. Download `tfplan-staging` artifact
3. Review with:
   ```bash
   terraform show tfplan-staging > staging-plan.txt
   ```
4. Confirm:
   - `aws_db_instance` or `aws_rds_cluster` is present with `multi_az = true`, `storage_encrypted = true`
   - `aws_elasticache_replication_group` is present with `automatic_failover_enabled = true`, encryption enabled
   - No unexpected `force-new-resource` or `destroy` actions on existing infrastructure
   - No hardcoded secrets in plan output

#### 4.4 Do Not Apply Yet

The workflow does **not** include an apply step. Apply to staging will be a separate manual or gated action after plan review.

---

### 5. Staging Runtime Environment Checklist

Before P0-007 (OTel) and P0-002 (DB HA) runtime validation can run, the following must exist in the staging environment.

#### 5.1 Cluster and Platform

| # | Check | How to Verify | Status |
|---|-------|-------------|--------|
| 1 | EKS cluster `fabric-staging` exists | `aws eks describe-cluster --name fabric-staging` | ☐ |
| 2 | kubectl context for staging works | `kubectl get nodes` returns Ready nodes | ☐ |
| 3 | ExternalSecrets controller installed | `kubectl get pods -n external-secrets` shows Running pods | ☐ |
| 4 | Configured secret backend reachable | ExternalSecrets `ClusterSecretStore` status shows `Ready` | ☐ |

> **Note:** Secret-backend setup (Vault, Infisical, etc.) is owned by the platform team. See `AGENTS.md` for local development setup. Do not block this runbook on secret-backend configuration — confirm only that ExternalSecrets can reach its backend.

#### 5.2 Observability

| # | Check | How to Verify | Status |
|---|-------|-------------|--------|
| 5 | OpenTelemetry Collector deployed | `kubectl get pods -n monitoring` shows collector Running | ☐ |
| 6 | Jaeger query endpoint reachable | `curl http://<jaeger-query>/api/services` returns service list | ☐ |

#### 5.3 Application Services

| # | Check | How to Verify | Status |
|---|-------|-------------|--------|
| 7 | Billing service deployed and healthy | `curl http://<billing>/health` returns 200 | ☐ |
| 8 | Layer 2.5-signal-refinery deployed and healthy | `curl http://<l2.5>/health` returns 200 | ☐ |
| 9 | Layer 7-billing deployed and healthy | `curl http://<l7>/health` returns 200 | ☐ |
| 10 | Services configured with OTel env vars | `kubectl get deployment billing -o yaml` shows `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` | ☐ |

#### 5.4 Database / Cache

| # | Check | How to Verify | Status |
|---|-------|-------------|--------|
| 11 | RDS/Aurora staging endpoint exists and reachable | `aws rds describe-db-instances --db-instance-identifier fabric-staging` shows `available` | ☐ |
| 12 | ElastiCache/Valkey staging replication group exists | `aws elasticache describe-replication-groups --replication-group-id fabric-staging` shows `available` | ☐ |
| 13 | Security groups allow EKS worker nodes -> RDS | `aws ec2 describe-security-group-rules` shows inbound from EKS node SG on 5432 | ☐ |
| 14 | Security groups allow EKS worker nodes -> ElastiCache | `aws ec2 describe-security-group-rules` shows inbound from EKS node SG on 6379 | ☐ |
| 15 | ExternalSecrets resolve DB secrets | `kubectl get externalsecret postgres-endpoint -n value-fabric` shows `SecretSynced` | ☐ |
| 16 | ExternalSecrets resolve Redis secrets | `kubectl get externalsecret redis-endpoint -n value-fabric` shows `SecretSynced` | ☐ |
| 17 | App pod can connect to PostgreSQL | `kubectl exec <pod> -- python -c "import psycopg2; psycopg2.connect(...)"` or similar | ☐ |
| 18 | App pod can connect to Redis | `kubectl exec <pod> -- redis-cli -h <host> PING` returns `PONG` | ☐ |

#### 5.5 Validation Scripts Ready

| # | Check | Command | Status |
|---|-------|---------|--------|
| 19 | RDS backup validation ready | `./scripts/ci/validate-rds-backup.sh fabric-staging` | ☐ |
| 20 | ElastiCache failover validation ready | `./scripts/ci/validate-elasticache-failover.sh fabric-staging` | ☐ |
| 21 | OTel trace receipt test ready | `pytest tests/backend_integrated/test_otel_trace_receipt.py -m backend_integrated` | ☐ |

---

### 6. Secret-Backend Reference

This runbook does **not** include detailed steps for configuring Vault, Infisical, or other secret backends. The following resources contain the relevant operational procedures:

- `AGENTS.md` — First-time setup including Infisical CLI login and local development environment
- Platform team secret-management runbooks (separate from this repository)

**Minimum requirement for P0 validation:**
- ExternalSecrets controller is installed in the staging cluster
- A `ClusterSecretStore` named `vault-backend` (or equivalent) is configured and shows `Ready`
- Secrets exist in the backend for:
  - `secret/data/fabric/postgres` (host, port, db, user, password, ssl_mode)
  - `secret/data/fabric/redis` (host, port, auth_token, ssl, db)
  - Service-specific secrets (API keys, tokens) as required by application manifests

---

### 7. After Setup — Status Update

After completing this runbook:

1. Confirm `AWS_TERRAFORM_ROLE_ARN` and `AWS_REGION` are configured in GitHub
2. Confirm Terraform backend resources exist
3. Trigger the Terraform CI workflow and verify the preflight job passes
4. Review the staging plan artifact
5. Apply to staging (manual or gated action, not in CI yet)
6. Verify the staging runtime checklist items above
7. Run the three P0 validation scripts
8. Append evidence to `reports/p0-blockers-staging-evidence-YYYY-MM-DD.md`

Do **not** mark any P0 blocker as production closed until all runtime evidence is captured.
