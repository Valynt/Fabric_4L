# Data Lifecycle Readiness Suite

## What This Suite Validates

This suite locks the platform policy for customer data creation, retention, export, soft deletion, hard deletion, archival, anonymization, and auditability. It is intentionally PR-safe and does not require live PostgreSQL, Neo4j, object storage, Stripe, or identity-provider access.

## Lifecycle Policy By Data Category

| Category | Examples | Retention | Export | Deletion behavior |
|---|---|---:|---|---|
| tenant_profile | Tenant name, domains, plan, region, lifecycle state | Tenant lifetime plus 30 day recovery window | Tenant export | Soft delete marks `deletion_pending`; hard delete replaces tenant-facing identifiers with tombstones while preserving billing and audit references |
| workspace_metadata | Workspace names, settings, memberships, feature flags | Tenant lifetime plus 30 day recovery window | Tenant export | Soft delete hides from active queries; hard delete removes workspace metadata after child records are purged or tombstoned |
| account_profile | Customer account records, CRM references, account stage | Tenant lifetime plus 30 day recovery window | Account and tenant export | Soft delete hides active account views; hard delete purges customer-controlled fields and keeps non-PII billing/audit references |
| user_identity | User IDs, email, display name, role membership | Tenant lifetime plus 30 day recovery window | Tenant export | Soft delete disables access; hard delete anonymizes PII and preserves surrogate user references for audit integrity |
| source_content | Crawled pages, uploaded source files, raw ingestion text | 30 days after superseded, deleted, or tenant closure unless legal hold applies | Tenant export when active and authorized | Soft delete stops processing; hard delete purges raw content and derived cache payloads |
| derived_knowledge | Extracted entities, claims, embeddings, graph relationships | Tenant lifetime plus 90 days unless source deletion or legal hold overrides | Tenant export | Soft delete removes from retrieval; hard delete removes tenant-owned graph/vector records and leaves tombstones for referential integrity |
| workflow_outputs | Agent runs, value cases, ROI models, generated documents | Tenant lifetime plus 90 days unless contract requires longer | Account and tenant export | Soft delete prevents editing/export except admin recovery; hard delete purges generated content and preserves minimal audit metadata |
| billing_records | Subscriptions, invoices, payment status, entitlement history | 7 years | Tenant export metadata only; no payment secrets | Never removed by customer hard deletion; retain legal ledger fields and detach/anonymize customer PII |
| audit_logs | Auth events, exports, deletion requests, privileged actions, policy decisions | 7 years minimum, separate from customer data retention | Tenant export as compliance metadata when authorized | Append-only; not hard deleted by tenant request; actor and tenant identifiers may be pseudonymized after hard deletion |
| system_telemetry | Metrics, traces, logs, job health, error summaries | 30 days for detailed logs, 13 months for aggregate metrics | Not included except audit-linked metadata | Redact or hash customer identifiers; lifecycle follows observability policy, not tenant export payloads |
| backups_archives | Database snapshots, object-store recovery copies, disaster recovery bundles | Backup window plus disaster recovery policy; no longer than required by runbook | Not directly exportable | Expire through backup lifecycle; deletion requests are applied to restored environments before customer access |

## Deletion Semantics

User, tenant, and workspace deletion follows a two-phase lifecycle:

1. Soft delete records the deletion request, actor, request ID, reason, and timestamp, then excludes the record from active reads, retrieval, exports, workflows, and write paths.
2. Hard delete is allowed only after the recovery window expires and legal, security, billing, and audit holds are clear.
3. Hard delete purges customer-controlled content and PII, anonymizes user identity fields, and preserves referential integrity through tombstone or surrogate identifiers.
4. Billing records and audit logs are retained under their own retention rules and must not be cascaded away with tenant-owned content.

Deletion must fail closed when tenant context is missing or mismatched. Request body tenant IDs never override authenticated tenant context.

## Stable Export Format

Exports are UTF-8 JSON documents by default. CSV may be generated for human billing reports, but JSON is the stable contract for lifecycle tests.

Required top-level fields for `data-lifecycle-export.v1`:

```json
{
  "schema_version": "data-lifecycle-export.v1",
  "export_id": "exp_...",
  "export_scope": "account|tenant",
  "tenant_id": "tenant_...",
  "subject": {
    "type": "account|tenant",
    "id": "..."
  },
  "generated_at": "2026-06-04T00:00:00Z",
  "requested_by": {
    "actor_id": "user_...",
    "actor_type": "user|service|support",
    "tenant_id": "tenant_..."
  },
  "data_categories": ["account_profile"],
  "resources": {},
  "redactions": [],
  "audit_chain": [],
  "checksums": {
    "algorithm": "sha256",
    "payload": "..."
  }
}
```

Exports must not contain payment secrets, provider tokens, password hashes, raw auth claims, cross-tenant records, deleted records that have passed hard-delete eligibility, or detailed system telemetry.

## Known Gaps

- LIVE_PURGE_REPLAY: this suite locks semantics but does not replay hard deletion against every production datastore.
- BACKUP_ERASURE_AT_RESTORE: backup expiry is policy-tested here; restore-time deletion replay remains an operations runbook check.
- PROVIDER_SIDE_EXPORTS: Stripe, identity-provider, and object-store native export jobs are represented by metadata only in local tests.

## How To Run

```bash
pytest tests/data_lifecycle/
pnpm test:data-lifecycle
```

## CI Artifact

CI should publish `artifacts/production-readiness/data-lifecycle/junit.xml`.
