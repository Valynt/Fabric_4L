# Observability and SLO Gates

## Required SLOs

| SLO | SLI | Window | Target | Owner |
|---|---|---|---|---|
| Source acceptance availability | Successful accepted / total accepted | 1h | 99.95% | layer1 |
| End-to-end workflow success | Successful L1-L6 completions / started | 24h | 99.9% | platform |
| Time to normalized source | p99 duration from source acceptance to normalized | 24h | ≤ 5 min | layer1 |
| Time to extracted signals | p99 from normalized to signal extraction | 24h | ≤ 10 min | layer2 |
| Time to Fabric Found Summary | p99 from signals to projected summary | 24h | ≤ 15 min | layer4 |
| Projection freshness | (now - latest projection update) | 5m | ≤ 1 min | data-platform |
| API latency | p99 request latency | 1h | ≤ 500 ms | platform |
| Workflow age | p99 age of in-progress workflows | 1h | ≤ 30 min | layer4 |
| Queue lag | p99 queue message age | 5m | ≤ 1 min | platform |
| Claim-lineage availability | Successful lineage queries / total | 1h | 99.9% | layer3 |
| Audit-event completeness | Workflows with complete audit / total | 24h | 100% | security |
| Tenant-isolation incidents | Count of cross-tenant events | 24h | 0 | security |
| Restore success | Successful restore drills / attempts | 90d | 100% | SRE |
| Data-loss rate | Lost records / total records | 24h | 0 | data-platform |

## Required trace dimensions

Every critical workflow must expose:

- Request/workflow ID
- Trace ID
- Tenant-safe context
- Current stage
- State transition
- Attempt count
- Queue age
- Processing latency
- Failure category
- Dependency status
- Artifact version
- Model and prompt version (where applicable)
- Final outcome
- Audit-event linkage

## Alert validation

Before release, prove that:

- Alerts fire under controlled test conditions.
- Alerts route to an active responder.
- Runbook links resolve.
- Recovery instructions are current.

## Observability gate

- `make gate-obs`
- `pnpm test:observability`
- `scripts/ci/check_observability_coverage.py`

## Breach actions

| Breach | Action |
|---|---|
| SLO error budget exhausted | Release freeze |
| Queue lag exceeds SLO | Scale workers or pause ingress |
| Tenant-isolation anomaly | Incident + auto-rollback |
| Audit-event completeness < 100% | Block release + investigate |
| Projection freshness exceeded | Alert + scale projectors |

## Evidence

Observability evidence is retained in `artifacts/obs/` for one year.
