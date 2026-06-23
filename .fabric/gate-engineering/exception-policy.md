# Exception Policy

## Purpose

Release gates protect invariants. This policy governs the rare cases where a gate cannot be satisfied before a required release decision and the risk is accepted under compensating controls.

## Prohibited overrides

The following gates may never be overridden:

- `pre_production.tenant_isolation` — cross-tenant data access
- `security.p0_auth_boundaries` — authorization bypass
- `ai_agent.structured_output` — fabricated evidence or unsupported financial claims
- `data.migration_safety` — incompatible or unsafe migration
- `deployment.artifact_integrity` — unsigned or untraceable artifact

## Required exception record

Every exception must be recorded in `.fabric/gate-engineering/exceptions/` as a JSON file named `<gate_id>-<YYYYMMDD>-<requester>.json` and validated against `exception-schema.json`. The record must contain:

| Field | Description |
|---|---|
| `gate_id` and `version` | Specific gate that failed |
| `failed_criterion` | Exact unmet criterion from the gate definition |
| `risk_quantification` | Numeric or qualitative risk statement |
| `affected_artifacts` | Image digests, commits, environments, tenants, features |
| `compensating_controls` | Concrete controls that offset the risk |
| `requester` | Person requesting the exception |
| `approver` | Person approving; must differ from requester when separation of duties applies |
| `created_at` and `expires_at` | UTC timestamps; no exception is permanent |
| `rollback_trigger` | Condition that forces immediate rollback |
| `remediation_owner` | Owner accountable for remediation |
| `remediation_deadline` | UTC timestamp |

## Process

1. Requester opens an exception record and attaches it to the release metadata.
2. Required approver reviews evidence and compensating controls.
3. CI validates the exception record against schema and checks expiration.
4. The release-readiness report includes the exception as a warning (non-blocking) or blocks if the gate is prohibited or the exception is expired.
5. An audit event is emitted with the exception record URI.

## Expiration

Exceptions auto-expire. The release gate that consumed the exception blocks the next release after expiration unless the underlying condition is remediated.

## Separation of duties

- A release requester cannot approve their own exception.
- A security exception must be approved by a security lead or CISO.
- A data-migration exception must be approved by the data-platform lead and release manager.

## Evidence

Exception records are retained for one year and are referenced from the release-readiness report.
