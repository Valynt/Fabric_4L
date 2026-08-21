# Workspace (live task state)

## Current task

P1 Observability & SLOs verification — Prometheus SLI alerting rules and Jaeger trace propagation. Verification evidence committed to `signoff-evidence/gates/observability-sli-jaeger-verification.md`.

## Status

Complete. All four todos done. 32 targeted tests pass. Evidence file committed and pushed on branch `bmsull560-verify-sli-and-trace-propagation`; PR #1374 review feedback (codex) addressed: L2 FastAPI telemetry gap and cross-layer alert label.

## What was done

- Audited `monitoring/alerting/layer-sli-rules-production.yml`: 19 alerts, all labels/annotations/runbook URLs valid, thresholds consistent across L1-L6.
- Verified W3C traceparent/tracestate, correlation-header aliasing, OTel collector → Jaeger export.
- Ran 32 targeted observability/contract/security/reliability/CI tests to green.
- Wrote and committed verification evidence; corrected it for the L2 telemetry gap and the cross-layer alert label qualification.

## Findings (drift)

- (A) SLI rules file not in any live Prometheus `rule_files` (not deployed).
- (B) L2 emits only `vf_*` metrics; SLI rules reference `layer2_http_*`/`layer2_health_status` — L2 alerts never fire; `initialize_metrics()` uncalled.
- (B2) L2 passes `instrument_telemetry=True` but omits `telemetry_service_name`; provider stays None, emits no FastAPI spans to Jaeger.
- (C) docker-compose path mismatch `./monitoring/prometheus.yml` vs actual.
- (D) L6 `layer6_health_status` uses `service=` label; SLI rule selects `{component="api"}` — availability SLI silently never fires.

## Active hypotheses / Next step

None in current task. Recommended outcome: file findings A-D/B2 as drift/debt and route fixes through normal PR CI path, not in-place on this verification branch.
