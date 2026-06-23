# Canary Policy

## Goal

A canary must prove real production behavior before traffic is increased. A canary with insufficient traffic remains inconclusive and blocks further promotion.

## Requirements

| Requirement | Definition |
|---|---|
| Minimum volume | At least 100 completed end-to-end workflows or 1000 requests per critical path |
| Minimum duration | 15 minutes, or until statistically significant, whichever is longer |
| Source types | Notes, web/search, audio, CRM, PDF, meetings where feasible |
| Completion | End-to-end completion through the final read model, not ingress success |
| Baseline | Comparison against current production baseline |
| Error rate | ≤ 0.1% or ≤ baseline + 0.05% |
| Latency | P99 ≤ baseline + 20% |
| Queue lag | ≤ SLO threshold |
| Worker failures | ≤ 0.1% |
| Database errors | ≤ 0.05% |
| Graph writes | Tenant-scoped and error rate ≤ 0.05% |
| Projection freshness | ≤ SLO threshold |
| Audit completeness | 100% of critical workflows emit audit events |
| Tenant isolation | No cross-tenant access anomalies |
| Evidence lineage | Source-to-summary lineage retrievable for ≥ 95% of workflows |

## Traffic progression

| Stage | Traffic % | Gate |
|---|---|---|
| Canary | 1% | canary.critical_paths |
| Pilot | 10% | canary.critical_paths + error-budget check |
| Beta | 50% | reliability readiness |
| GA | 100% | post_deployment.synthetic_workflows |

## Auto-rollback triggers

- Error rate exceeds threshold
- Latency exceeds threshold
- Any critical synthetic workflow fails
- Tenant isolation anomaly detected
- Audit event completeness drops below 100%
- Queue lag exceeds SLO
- Human rollback command

## Inconclusive canary

If the canary does not receive enough traffic to satisfy the minimum volume, the result is `INCONCLUSIVE` and promotion pauses. It does not pass.

## Evidence

Canary evidence is recorded in `artifacts/release/canary/<stage>.json` and referenced in the release-readiness report.
