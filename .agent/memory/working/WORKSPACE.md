# Workspace (live task state)

## Current task

P1 Observability & SLOs verification — Prometheus SLI alerting rules and Jaeger trace propagation (verification-only; no repo files modified).

## Status

Complete. All four todos done. 32 targeted tests pass; Jaeger trace propagation verified. Four drift findings documented (A–D) in the verification report (artifacts, not repo).

## What was done

- Audited `monitoring/alerting/layer-sli-rules-production.yml`: 19 alerts, all labels/annotations/runbook URLs valid, thresholds consistent across L1–L6.
- Verified W3C traceparent/tracestate, correlation-header aliasing, OTel collector → Jaeger export, and middleware wiring across all layer entrypoints via shared `create_fabric_app()`.
- Ran 32 targeted observability/contract/security/reliability/CI tests to green.
- Wrote verification report covering three + D drift findings.

## Findings (drift)

- (A) SLI rules file not in any live Prometheus `rule_files` (not deployed).
- (B) L2 emits only `vf_*` metrics; SLI rules reference `layer2_http_*`/`layer2_health_status` — L2 alerts never fire; `initialize_metrics()` uncalled.
- (C) docker-compose path mismatch `./monitoring/prometheus.yml` vs actual.
- (D) L6 `layer6_health_status` uses `service=` label; SLI rule selects `{component="api"}` — availability SLI silently never fires.

## Active hypotheses / Next step

None in current task. Recommended outcome: file findings as drift/debt; route fixes through normal PR CI path (do not fix in-place on verification-only branch).
