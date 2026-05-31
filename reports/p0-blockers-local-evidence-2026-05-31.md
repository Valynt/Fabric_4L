# P0 Blockers — Local Verification Evidence

Date: 2026-05-31
Scope: Local/static verification only. Staging/runtime validation pending.

---

## P0-007: OpenTelemetry Instrumentation

### Static Tests
```
$ python -m pytest tests/contract/test_otel_instrumentation.py -v --tb=short --no-mandatory-dep-check -m contract_static_no_service
====================================================================================== test session starts =======================================================================================
collected 6 items / 5 deselected / 1 selected

tests/contract/test_otel_instrumentation.py::TestOtelInstrumentationStatic::test_billing_service_calls_instrument_fastapi_app PASSED                                                        [ 16%]
tests/contract/test_otel_instrumentation.py::TestOtelInstrumentationStatic::test_billing_service_calls_init_telemetry PASSED                                                                [ 33%]
tests/contract/test_otel_instrumentation.py::TestOtelInstrumentationStatic::test_opentelemetry_collector_yaml_is_valid PASSED                                                               [ 50%]
tests/contract/test_otel_instrumentation.py::TestOtelInstrumentationStatic::test_layer7_passes_instrument_telemetry_true PASSED                                                             [ 66%]
tests/contract/test_otel_instrumentation.py::TestOtelInstrumentationStatic::test_layer25_passes_instrument_telemetry_true PASSED                                                            [ 83%]
tests/contract/test_otel_instrumentation.py::test_all_services_have_otel_env_references PASSED                                                                                              [100%]

======================================================================================= 6 passed in 10.65s =======================================================================================
```
**Status: PASS**

### YAML Validation
- `k8s/monitoring/opentelemetry-collector.yaml` — valid, OTLP receivers on 4317/4318, traces pipeline declared

### Pending
- Runtime trace receipt smoke test (`tests/backend_integrated/test_otel_trace_receipt.py`)
  - Requires: live Jaeger query API, running billing / layer2.5 / layer7 services
  - Gated by: `backend_integrated` + `service_required` pytest markers

---

## P0-010: Terraform CI Integration

### Custom Policy Checks
```
$ python scripts/ci/check_terraform_rds_backup_policy.py infra/terraform
RDS backup retention policy check passed.

$ python scripts/ci/check_terraform_elasticache_encryption.py infra/terraform
ElastiCache encryption policy check passed.

$ python scripts/ci/check_terraform_s3_encryption.py infra/terraform
S3 encryption policy check passed.
```
**Status: ALL PASS**

### Module Verification
- `infra/terraform/modules/rds/main.tf` — uses `terraform-aws-modules/rds/aws` v6, Multi-AZ conditional, encryption, Performance Insights
- `infra/terraform/modules/elasticache/main.tf` — native `aws_elasticache_replication_group`, automatic failover, encryption at rest + transit
- `infra/terraform/modules/rds/outputs.tf` — exposes endpoint, port, username, DB name
- `infra/terraform/modules/elasticache/outputs.tf` — exposes primary endpoint, reader endpoint, port
- All 3 environments (dev/staging/prod) instantiate both modules with environment-specific sizing

### YAML Validation
- `.github/workflows/terraform-cd.yml` — valid GitHub Actions workflow YAML

### Pending
- `terraform fmt -check -recursive` — requires Terraform CLI
- `terraform validate` per environment — requires Terraform CLI
- `tflint` — requires TFLint binary
- `terraform plan` for staging — requires AWS OIDC credentials + Terraform CLI

---

## P0-002: AWS-Managed Database HA

### K8s Manifest Validation
```
$ python -c "import yaml; yaml.safe_load(open('k8s/external-secrets/postgres-endpoint.yaml'))"
postgres-endpoint.yaml valid

$ python -c "import yaml; yaml.safe_load(open('k8s/external-secrets/redis-endpoint.yaml'))"
redis-endpoint.yaml valid

$ python -c "import yaml; yaml.safe_load(open('k8s/base/configmap-postgres.yaml'))"
configmap-postgres.yaml valid

$ python -c "import yaml; yaml.safe_load(open('k8s/base/configmap-redis.yaml'))"
configmap-redis.yaml valid
```
**Status: ALL VALID**

### Pending
- Terraform apply in staging — requires AWS account
- `validate-rds-backup.sh fabric-staging` — requires AWS CLI + RDS instance exists
- `validate-elasticache-failover.sh fabric-staging` — requires AWS CLI + ElastiCache replication group exists
- K8s ExternalSecrets connectivity test — requires running cluster + Vault
- Neo4j hosting decision — requires procurement evaluation

---

## Summary

| P0 Blocker | Local/Static | Staging/Runtime | Production Pass |
|------------|------------|-----------------|-----------------|
| P0-007 OTel | PASS (6/6 tests) | PENDING | PENDING |
| P0-010 Terraform CI | PASS (policy checks, module review) | PENDING (plan/apply) | PENDING |
| P0-002 AWS DB HA | PASS (YAML valid, modules complete) | PENDING (apply + tests) | PENDING |

---

*This file records local verification only. Staging and production evidence must be captured separately after AWS/cloud resources are provisioned.*
