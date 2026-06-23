# Task 46 — Monitoring Readiness (P0)

This plan completes production monitoring and alert wiring across Docker Compose and Kubernetes, with full live runtime validation required for Compose and manifest-parity plus CI dry-run validation for Kubernetes.

## Scope and Success Criteria

- Cover both deployment paths: `docker-compose.full.yml` (P0) and `k8s/*.yml` (parity/hardening).
- Resolve Prometheus target correctness so monitored jobs map to real service DNS/ports.
- Ensure Alertmanager dependency is either fully wired end-to-end or explicitly removed/disabled with rationale.
- Validate alert rules load successfully and queries reference real metrics.
- Leave Task 47 to enforce full in-cluster runtime E2E validation for Kubernetes.

## Phase 1: Static Monitoring Audit and Wiring Corrections

1. Compose wiring audit
   - Validate `monitoring/prometheus/prometheus.yml` against service names/ports in `docker-compose.full.yml`.
   - Confirm `rule_files` path resolves inside Prometheus container.
   - Confirm Grafana datasource/provider files align with Compose service DNS and mounted paths:
     - `monitoring/grafana/provisioning/datasources/prometheus.yml`
     - `monitoring/grafana/provisioning/dashboards/value-fabric.yml`
   - Verify dashboard queries in `monitoring/grafana/dashboards/*.json` are compatible with exported metric names.

2. Alertmanager decision and implementation
   - Preferred: add working Alertmanager service/config wiring in Compose (service, config file, mounts, network, health check).
   - Fallback: explicitly remove/disable `alerting` stanza reference in Prometheus with clear rationale if Alertmanager is intentionally deferred.

3. Alert rules validity pass
   - Review `monitoring/alerting/rules.yml` expressions for metric-name consistency and realistic labels.
   - Ensure no dead/never-emitted metric dependencies remain in critical alerts.

## Phase 2: Compose Runtime Validation (Hard Gate)

1. Bring up stack and monitoring components
   - Start monitoring + app stack using Compose.
   - Confirm Prometheus reaches all intended scrape targets.

2. Runtime checks (required)
   - Prometheus `/targets`: all expected jobs healthy (or documented expected exceptions).
   - Prometheus rules endpoint/status: rules loaded, no parse/eval errors.
   - Alertmanager smoke path: test alert reaches Alertmanager ingestion path.
   - Grafana datasource health: Prometheus datasource resolves and dashboard queries return data where expected.

3. Evidence capture
   - Capture command outputs and endpoint checks for:
     - target health summary
     - rule load status
     - alert pipeline smoke result

## Phase 3: Kubernetes Parity + CI Validation (Task 46 Gate)

1. Manifest parity updates
   - Add/align K8s monitoring manifests (Prometheus/Alertmanager config + scrape wiring) under `k8s/` and/or `monitoring/` as appropriate.
   - Ensure Kubernetes service names/ports match scrape config jobs.

2. CI server-side dry-run validation
   - Add/update CI step(s) to run server-side dry-run/apply validation for monitoring manifests.
   - Validate rendered manifests and schema-level correctness without requiring a live manual cluster test.

3. Runtime playbook documentation
   - Document concrete operator runbook commands for post-deploy verification in K8s:
     - Prometheus target checks
     - rule load checks
     - Alertmanager route smoke checks

## Planned File Touches

- `monitoring/prometheus/prometheus.yml`
- `monitoring/alerting/rules.yml`
- `monitoring/grafana/provisioning/datasources/prometheus.yml` (if needed)
- `monitoring/grafana/provisioning/dashboards/value-fabric.yml` (if needed)
- `monitoring/grafana/dashboards/*.json` (only if metric/query mismatches are confirmed)
- `docker-compose.full.yml`
- `k8s/` monitoring-related manifest files (new and/or existing)
- CI workflow file(s) under `.github/workflows/` for dry-run enforcement
- Monitoring/K8s runbook documentation file(s)

## Acceptance Criteria

- Compose:
  - Prometheus scrape targets map to real Compose service names and show healthy in `/targets`.
  - Alert rules load without errors.
  - Alertmanager path is operational (or dependency explicitly removed with rationale and no dead references).
  - Smoke evidence captured for targets/rules/alerts.
- Kubernetes:
  - Monitoring manifests are parity-aligned with service topology.
  - CI server-side dry-run passes for monitoring manifests.
  - Runtime verification playbook is documented for Task 47 execution.

## Risks and Mitigations

- Metric name drift between dashboards/rules and service exporters.
  - Mitigation: verify via live `/metrics` sampling before changing dashboard/rule queries.
- Alert noise from broad thresholds.
  - Mitigation: keep thresholds unchanged for Task 46 unless clearly broken; focus on wiring correctness.
- Environment blockers (e.g., Docker daemon not running).
  - Mitigation: perform static validation first, then runtime checks when prerequisites are available.
