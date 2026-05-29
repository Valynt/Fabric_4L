# Value Fabric — Log Retention Policy

**Status:** Active  
**Owner:** Platform Engineering  
**Review cycle:** Annual  
**Last reviewed:** 2025-01-01

---

## Summary

| Tier | Storage | Retention |
|---|---|---|
| Hot (queryable) | Loki primary storage (local filesystem or S3-backed) | **30 days** |
| Cold (archival) | Object storage (S3 / GCS) | **1 year** |
| Audit logs | PostgreSQL `audit_events` table | **7 years** (regulatory) |
| Security / access logs | Dedicated SIEM / S3 | **1 year** |

---

## Hot Tier (30 Days)

Loki is configured with `table_manager.retention_period: 720h` (30 days).
Logs are deleted from primary storage automatically after this period.

Configuration file: `monitoring/loki/local-config.yaml`

Covers:
- Application logs from all six platform layers (L1–L6, L7)
- Infrastructure logs (Postgres, Redis, Neo4j, MinIO)
- Kubernetes pod/container logs (via Fluent-Bit DaemonSet)

---

## Cold Tier (1 Year)

Logs older than 30 days that must be retained for compliance or debugging are
shipped to object storage before Loki deletes them.

Implementation options:
1. **Loki S3 backend with compactor** — set `compactor.retention_enabled: true`
   and configure an S3-backed `common.storage`. The compactor enforces per-stream
   retention rules and automatically moves data to cold tiers.
2. **Fluent-Bit S3 output plugin** — a secondary output rule mirrors all log
   streams to an S3 bucket with a 365-day lifecycle policy. See
   `monitoring/fluent-bit/` for the existing Fluent-Bit configuration.

Cold logs are compressed (gzip) and indexed by date partition:
```
s3://<bucket>/logs/year=YYYY/month=MM/day=DD/<stream>.log.gz
```

Retrieval SLA: cold logs should be accessible within 4 hours of a request.

---

## Audit Logs (7 Years)

Business-critical audit events (`audit_events` table in PostgreSQL) are subject
to a 7-year retention requirement for financial and compliance purposes.  These
are NOT managed by Loki — they are managed by the PostgreSQL backup and
point-in-time recovery pipeline.  See
`docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md`.

Audit log records must never be hard-deleted.  Soft-deletion is permitted only
for PII erasure requests under GDPR / CCPA (see L5 data erasure runbook).

---

## Security / Access Logs (1 Year)

Authentication events, RBAC decisions, and API gateway access logs are
forwarded to a SIEM or dedicated S3 bucket with a 365-day lifecycle policy.
These logs support incident investigation and are subject to the same access
controls as the primary application.

---

## PII Considerations

Logs must not contain:
- Full API keys or secret values
- Passwords or tokens (mask at ingestion with Fluent-Bit `modify` filter)
- Personal Identifiable Information (PII) in plaintext

Fluent-Bit masking rules are configured in `monitoring/fluent-bit/`.
If PII leaks into logs, a GDPR erasure request requires redaction across both
hot and cold tiers.  Coordinate with the Data Privacy team.

---

## Enforcement

| Layer | Mechanism |
|---|---|
| Loki hot tier | `table_manager.retention_period: 720h` in `monitoring/loki/local-config.yaml` |
| S3 cold tier | S3 lifecycle policy: `Expiration.Days: 365` on the log bucket |
| Audit logs | PostgreSQL backup retention; no automated deletion |
| SIEM bucket | S3 lifecycle policy: `Expiration.Days: 365` on the SIEM bucket |

---

## Alerting

If log ingestion gaps exceed 5 minutes, an alert fires via `layer1-alerts.yml`.
Loki compactor errors are surfaced via the Grafana dashboards in
`monitoring/grafana/`.

---

## References

- `monitoring/loki/local-config.yaml` — Loki hot-tier configuration
- `monitoring/fluent-bit/` — Fluent-Bit pipeline and masking rules
- `docs/troubleshooting/runbooks/infrastructure/postgres-backup-restore.md`
- `SECURITY.md` — platform security policy
