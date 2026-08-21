# P1 Observability & SLOs Verification Evidence

- **Task**: P1 Observability & SLOs - Verify Prometheus SLI alerting rules and Jaeger trace propagation
- **Branch**: `bmsull560-verify-sli-and-trace-propagation`
- **Verified Date**: 2026-08-20
- **Target Invariant**: (1) Prometheus SLI alerting rules in `monitoring/alerting/layer-sli-rules-production.yml` are well-formed, correctly labeled, and aligned with live layer instrumentation; (2) W3C trace context propagates across all layers to Jaeger.

---

## 1. Executive Summary

This is a **verification-only** deliverable: no production source code was modified. It audits the SLI alerting contract, confirms W3C trace propagation wiring across the six-layer platform, runs the targeted observability/contract test suites, and records production-readiness drift findings that should be routed through normal change CI.

The SLI rules file is **structurally valid** and **metadata-complete** (19 alerts), and Jaeger trace propagation is **correctly wired** across all layer entrypoints. However, the audit surfaced **four drift findings** (A-D) that mean the SLI rules, as currently deployed, would not function as intended for Layers 2 and 6, and the SLI file itself is not loaded by live Prometheus.

---

## 2. Verification - Prometheus SLI Alerting Rules

**File audited:** `monitoring/alerting/layer-sli-rules-production.yml`

| Check | Result |
|---|---|
| YAML structure / alerts parse | **PASS** - 1 group `layer-sli-production`, 19 alerts |
| Required labels (`severity`, `environment: production`, `oncall_owner`, `layer`) | **PASS** - all 19 alerts |
| Required annotations (`summary`, `description`, `runbook_url`) | **PASS** - all 19 alerts |
| Runbook URLs resolve to existing files | **PASS** - all under `docs/troubleshooting/runbooks/` |
| Latency threshold (p95) | **PASS** - `> 1.5s` consistent L1-L6 |
| Error-rate threshold | **PASS** - `> 0.01` (1%) consistent L1-L6 |
| Availability threshold | **PASS** - `< 1` over 10m window consistent L1-L6 |
| Metadata checker `scripts/ci/check_production_alert_metadata.py` | **PASS** - 19 alerts, 0 failures |
| CI test `tests/ci/test_production_alert_metadata.py` | **PASS** |

## 3. Verification - Jaeger Trace Propagation

- **W3C trace context** (`packages/shared/src/value_fabric/shared/observability/w3c_trace_context.py`): verified `traceparent`/`tracestate` parse/serialize/round-trip (00-32hex-16hex-2hex format).
- **Correlation headers** (`trace_context.py`): verified `X-Request-ID` + aliases `X-Correlation-ID` / `X-Trace-ID`.
- **OTel collector** (`monitoring/otel-collector.yaml`): OTLP receiver + tail sampling + Jaeger export verified.
- **Jaeger datasource** (`monitoring/grafana/provisioning/datasources/jaeger.yml`): verified.
- **Middleware wiring**: `init_telemetry()` + `FastAPIInstrumentor.instrument_fastapi_app()` wired into all layer entrypoints via shared `create_fabric_app()` in `packages/shared/src/value_fabric/shared/fastapi_framework/app.py` (211-250). W3C extraction/injection enabled.

## 4. Test Suite Validation

32 targeted tests pass (manual venv, `--no-mandatory-dep-check`):

- `tests/observability/test_trace_propagation.py`
- `tests/security/test_trace_correlation_contract.py`
- `tests/contract/test_service_observability_contracts.py`
- `tests/reliability/test_slo_definitions.py`
- `tests/ci/test_production_alert_metadata.py`

Not run: one contract test requiring live services (timed out - out of static scope, no containers available on this machine; Docker/promtool unavailable).

---

## 5. Drift Findings (production-readiness gaps)

### Finding A - SLI rules file not wired into live Prometheus
`layer-sli-rules-production.yml` is only referenced by docs, `scripts/ci/check_production_alert_metadata.py`, `tests/ci/test_production_alert_metadata.py`, and `.fabric/gate-engineering/contract-inventory.json`. It is **NOT** in any live Prometheus `rule_files`:
- `monitoring/prometheus/prometheus.yml` mounts `recording-rules.yml` + `alerting/rules.yml` only.
- `k8s/base/monitoring-prometheus.yml` mounts embedded `rules.yml` configmap.
- `infra/compose/docker-compose.observability.yml` / `docker-compose.full.yml` mount `monitoring/alerting-rules.yml` / `monitoring/alerting/rules.yml`.

**Impact:** The audited SLI alert set is not the one actually deployed. `monitoring/alerting/rules.yml` (the live one) is a separate, partially-duplicated file.

### Finding B - Layer 2 metric-name drift (critical)
The SLI rules for L2 and the live `monitoring/alerting/rules.yml` reference `layer2_http_request_duration_seconds_bucket`, `layer2_http_requests_total{status_code=~"5.."}`, and `layer2_health_status{component="api"}`. But L2's live metrics module (`services/layer2-extraction/src/layer2_extraction/metrics/prometheus_metrics.py`) only emits **`vf_`-prefixed** names (`vf_health_status`, `vf_extraction_outcomes_total`, `vf_schema_validation_failures_total`, `vf_extraction_retries_total`, `vf_model_latency_seconds`, `vf_extraction_confidence`, `vf_cache_failures_total`, `vf_prompt_injection_attempts_total`, `vf_auth_failures_total`). Additionally `initialize_metrics()` is defined but never called in L2 service source, and `health.py` reads `metrics._metrics.get("requests_total")`/`active_connections` which the `vf_`-based module never populates.

**Impact:** L2 latency/error/availability SLI alerts will never fire - they reference metrics L2 never emits. Single most actionable finding.

### Finding C - docker-compose path mismatch
`infra/compose/docker-compose.observability.yml` mounts `./monitoring/prometheus.yml`, but the actual file is `monitoring/prometheus/prometheus.yml`. Prometheus container would fail to load config in that compose path.

### Finding D - Layer 6 availability selector label mismatch
The L6 availability rule selects `layer6_health_status{component="api"}`, but L6 emits `layer6_health_status` with a **`service=` label** (`set_health_status(healthy, service=SERVICE_NAME)`, prometheus_metrics.py 158-161). The `{component="api"}` selector never matches, so L6 availability SLI would silently never fire.

---

## 6. Recommendation & Sign-off

This is a P1 **Verify** task on a verification-only branch. Recommend **documenting** findings (as done here) rather than fixing:
- Fixing B/D would change metric names/labels in L2 and L6 production code - a repo-wide change touching multiple services.
- A fix would require reconciling `layer-sli-rules-production.yml`, `alerting/rules.yml`, Prometheus `rule_files`, and docker-compose wiring simultaneously to avoid a half-migrated state.

**Conclusion:** File drift findings A-D as debt/blockers and drive fixes through the normal change CI path, not in-place on this verification branch.

## Residual Risk

- Metrics-prefix alignment confirmed for L1 (`layer1_`), L3 (`value_fabric_`), L4 (`layer4_`), L5 (`layer5_`), L6 (`layer6_`), except Finding D (L6 health label).
- Static validation only: Docker/promtool unavailable, so PromQL was not executed against a live collector.
- One live-service contract test not run (no containers).