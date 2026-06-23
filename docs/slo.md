# Service Level Objectives

> Canonical SLO reference for the Value Fabric platform.  
> Detailed SLOs and burn-rate math: `docs/operations/SLOs.md`  
> Machine-readable performance targets: `docs/slo/performance-slo.v1.json`  
> SLO breach runbook: `docs/troubleshooting/runbooks/application/slo-breach-response.md`

## Scope

This document states the SLOs, SLIs, and alerting thresholds that must be met for the platform to be considered production-ready. All SLOs are measured over a 30-day rolling window unless noted otherwise.

## Platform SLOs

| SLO | Target | SLI | Rationale |
| --- | ------ | --- | --------- |
| Availability | 99.9% | `http_2xx_rate / total_requests` | Enterprise B2B SaaS baseline; ~43 min monthly error budget |
| Latency (p99) | < 2s | `histogram_quantile(0.99, http_request_duration_seconds)` | API responsiveness for interactive use |
| Error rate | < 0.1% | `http_5xx_rate / total_requests` | Avoid customer-visible failures |
| Synthetic health | 100% | `probe_success` for `/health` endpoints | Early detection of layer outages |

## Layer SLOs

| Layer | Availability | Latency | Success / Quality | Error Budget |
| ----- | ------------ | ------- | ----------------- | ------------ |
| L1 Ingestion | 99.9% | p99 < 5 min (Celery) | Task success 99.5% | 0.1% |
| L2 Extraction | 99.5% | p99 < 30s | Extraction success 98% | 0.5% |
| L3 Knowledge | 99.9% | p99 < 500ms graph, <1s vector | Query success 99.5% | 0.1% |
| L4 Agents | 99.5% | p99 < 5 min workflow | Workflow success 95% | 0.5% |
| L5 Ground Truth | 99.5% | p99 < 2s | Eval pass rate > 85% | 0.5% |
| L6 Benchmarks | 99% | p99 < 30s | Report success 99% | 1% |

## Alerting Rules

Multi-window burn-rate alerts are configured in `monitoring/alerting/layer-sli-rules-production.yml`:

| Burn Rate | Lookback | Alert Threshold | Meaning |
| --------- | -------- | ----------------- | ------- |
| 14.4x | 1h | 2% budget burned | Page on-call |
| 6x | 6h | 5% budget burned | High-priority ticket |
| 2x | 3d | 10% budget burned | Review in next stand-up |

## Error Budget Policy

1. **Exhausted 50%** — SRE lead reviews; reliability work takes priority over new features.
2. **Exhausted 75%** — Feature freeze on affected layer until SLO is restored.
3. **Exhausted 100%** — Post-incident required; launch block for dependent services.

## Compliance & Review

- SLOs are reviewed quarterly and after any production incident.
- All SLOs are tracked in Grafana dashboards under `monitoring/grafana/dashboards/`.
- SLO evidence is collected by `scripts/perf/evaluate_slo.py` and `tests/reliability/test_slo_definitions.py`.
