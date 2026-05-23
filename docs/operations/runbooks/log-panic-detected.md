# Runbook: LogPanicDetected

## Overview

A panic, FATAL error, or unhandled exception has been observed in service logs. Unlike gradual degradation alerts, panics represent an unexpected code path that crashes a process thread or pod. Even if the orchestrator restarts the container quickly, the root cause must be investigated to prevent recurrence and data corruption.

## Trigger

- **Alert:** `LogPanicDetected`
- **Dashboard:** [Value Fabric Operational](../../monitoring/grafana/dashboards/value-fabric-operational.json)
- **Detection:**
  - Loki query: `sum by (layer, service) (rate({job="fluent-bit"} |~ "panic|PANIC|FATAL|UnhandledException" [1m])) > 0`
  - Fires on first occurrence (1-minute evaluation, 1-minute hold)

## Impact

- **Severity:** P1 - Critical
- **User Impact:** Request failures for the affected request; potential pod restart causing brief latency spike
- **Business Impact:** In-flight operations may be dropped; agent checkpoints may not persist
- **Data Impact:** Risk of partial writes or orphaned records if panic occurs mid-transaction

## Diagnosis

### 1. Capture the Full Stack Trace

```bash
# Retrieve the exact panic line and surrounding context
kubectl logs -n value-fabric -l app=<service> --since=10m | grep -A 20 -iE "panic|fatal|unhandledexception"

# If logs have rotated, query Loki for the trace
logcli query '{job="fluent-bit",service="<service>"} |~ "panic|PANIC|FATAL|UnhandledException"' --since=30m --limit=50
```

### 2. Identify the Triggering Request or Job

```bash
# Look for the request ID / trace ID adjacent to the panic
kubectl logs -n value-fabric -l app=<service> --since=10m | grep -B 5 -iE "panic|fatal" | grep -iE "trace_id|request_id|job_id"

# Cross-reference with Jaeger using the trace ID
kubectl exec -n value-fabric deployment/jaeger -- \
  curl -s "http://localhost:16686/api/traces/<trace_id>" | jq '.data[0].spans[] | {operationName, duration, tags}'
```

### 3. Check Pod Restart Count

```bash
# Confirm if the panic caused a restart
kubectl get pods -n value-fabric -l app=<service> -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].restartCount}{"\n"}{end}'

# Check events for CrashLoopBackOff
kubectl get events -n value-fabric --field-selector reason=BackOff | tail -10
```

### 4. Reproduce Locally (if safe)

```bash
# Run the service test suite focusing on the affected module
pytest services/<service>/tests/ -k <module_name> -x -v

# If the panic is data-dependent, extract the triggering payload from logs and create a minimal reproduction case
```

## Resolution

| Scenario | Action |
|---|---|
| Known bug with deployed fix | Verify the fix is in the latest image; trigger a rollout |
| New bug from recent deploy | Roll back immediately: `kubectl rollout undo deployment/<service> -n value-fabric` |
| Data-dependent edge case | Null-guard the offending line; add unit test with the triggering payload; deploy hotfix |
| Dependency panic (driver, client library) | Pin or upgrade the dependency; verify in staging before prod rollout |
| Resource-induced panic (OOM killer) | Follow [HighMemoryUsage](../troubleshooting/runbooks/infrastructure/high-memory-usage.md) runbook |

## Escalation

1. **On-call engineer** acknowledges within 2 minutes
2. **If panic recurs within 15 minutes**, page platform lead; consider rollback
3. **If panic affects write-path or causes data inconsistency**, declare incident immediately

## Post-Incident

- Add a unit or integration test that exercises the panic path
- Update Sentry/error-tracking fingerprint rules if applicable
- Review the language-specific panic-safety checklist (e.g., Python `try/finally` for DB sessions, Rust `unwrap` audit)
