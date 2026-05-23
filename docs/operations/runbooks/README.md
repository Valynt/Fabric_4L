# Operations Runbooks

This directory contains runbooks for log-based and operational alerts that span multiple layers of the Value Fabric platform. Metric-based runbooks live in [`docs/troubleshooting/runbooks/`](../../troubleshooting/runbooks/).

## Index

| Alert | File | Severity | Driver |
|---|---|---|---|
| **LogErrorSpike** | [log-error-spike.md](log-error-spike.md) | warning | Loki (LogQL) |
| **LogPanicDetected** | [log-panic-detected.md](log-panic-detected.md) | critical | Loki (LogQL) |
| **LogTenantIsolationFailure** | [tenant-isolation-failure.md](tenant-isolation-failure.md) | critical | Loki (LogQL) |
| **LogDatabasePoolExhaustion** | [database-pool-exhaustion.md](database-pool-exhaustion.md) | critical | Loki (LogQL) |
| **LogAuthAnomaly** | [auth-anomaly.md](auth-anomaly.md) | warning | Loki (LogQL) |

## Policy links

- Severity matrix and escalation policy: [docs/operations/severity-escalation-policy.md](../severity-escalation-policy.md)
- MTTA/MTTR reporting process: [docs/operations/mtta-mttr-reporting.md](../mtta-mttr-reporting.md)
- Postmortem template and corrective actions: [docs/operations/postmortem-template.md](../postmortem-template.md)
