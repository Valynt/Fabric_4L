# Customer Data Export or Deletion Runbook

## Purpose

Use this runbook for approved customer requests to export or delete tenant-owned data. This is a governed operation: never run ad hoc unscoped queries, never delete shared reference data, and never bypass legal hold or retention requirements.

## Trigger

An authenticated, approved export/deletion request reaches its execution window or a privacy deadline is at risk.

## Severity

SEV1 for cross-tenant disclosure or unauthorized deletion; SEV2 for deadline/data-integrity risk; SEV3 for a blocked request with time remaining.

## Preconditions

- Confirm the incident/request owner, affected environment, authorized tenant scope, and required approvals.
- Verify access to the relevant dashboards, audit records, secrets, backups, and deployment metadata.
- Capture the current version and state before making changes; destructive operations require explicit approval.

## Immediate Actions

1. Stop or freeze the smallest unsafe scope and declare the severity.
2. Preserve logs, traces, audit records, identifiers, configuration, and timestamps before mutation or restart.
3. Notify the owning on-call and Security when authorization, privacy, or tenant isolation may be affected.

## Diagnosis Steps

1. Confirm the trigger, timeline, affected tenants/customers, and last known-good state.
2. Correlate alerts, logs, traces, audit events, recent deployments, configuration changes, and dependency health.
3. Test whether impact is tenant-specific, regional, provider-specific, deployment-specific, or global.

## Resolution Steps

1. Apply the least-risk reversible correction described in the procedure details below.
2. Preserve fail-closed controls, tenant scope, contract compatibility, and auditability.
3. Record commands, approvals, state transitions, and the reason for the selected resolution.

## Validation

- Re-run the related gates and targeted service checks.
- Validate the affected customer path and a known-unaffected control tenant where tenant data is involved.
- Confirm alerts clear, audit evidence is complete, and no new errors or cross-tenant results appear.

## Rollback / Fallback

Return to the captured last known-good deployment, configuration, routing, or data artifact if validation fails. Keep the affected capability contained when no safe fallback preserves security and tenant isolation.

## Customer / Stakeholder Communication

Use the declared severity cadence. Report confirmed scope, customer impact, mitigation, residual risk, and next update time; never include secrets, raw customer data, or another tenant's identifiers.

## Evidence to Preserve

Preserve alert and dashboard snapshots, UTC timestamps, affected tenant/customer IDs, deployment SHAs, sanitized logs/traces, audit events, approvals, commands, gate outputs, and validation results in the incident or request record.

## Related Gates

- `tenant-isolation-gate`; mandatory security regression gate; contract checks; backup/restore readiness gate before destructive deletion; production-readiness gate.

## Related Runbooks

- ./investigate-data-corruption.md, ../security/respond-to-tenant-data-exposure.md, ../backup-disaster-recovery.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Customer data subject export, deletion, tenant offboarding, and evidence retention coordination across Value Fabric layers.  
> **Primary owners:** Customer Operations, Data Governance, Security, service owners for affected layers.

### Purpose

Use this runbook for approved customer requests to export or delete tenant-owned data. This is a governed operation: never run ad hoc unscoped queries, never delete shared reference data, and never bypass legal hold or retention requirements.

### Intake Requirements

- Request ID and requesting customer/tenant.
- Verified requester identity and authority.
- Operation type: export, deletion, or both.
- Tenant ID(s), environment, and product area.
- Deadline, contractual/regulatory driver, and approval from Data Governance.
- Legal hold, security investigation, billing, or audit retention constraints.

### Approval Gates

| Gate | Owner | Required before action |
|---|---|---|
| Identity and authorization | Customer Operations | Requester is verified tenant admin or approved legal contact. |
| Scope | Data Governance | Tenant IDs and data classes are approved. |
| Retention/legal hold | Legal/Security | No deletion conflict or approved exception documented. |
| Technical plan | Service owners | Export/delete plan covers all layers and derived stores. |

### Data Map Checklist

Include tenant-owned data in:

- Layer 1 ingestion jobs, crawl artifacts, source documents, and provenance.
- Layer 2 extraction events, entities, RDF/OWL outputs, and provenance.
- Layer 3 graph nodes/relationships, evidence, embeddings, vector indexes, and caches.
- Layer 4 workflow state, checkpoints, prompts, tool traces, and generated business cases.
- Layer 5 TruthObjects, claim validation, and maturity evidence.
- Layer 6 tenant benchmark usage, peer-comparison outputs, and reports.
- API gateway auth/audit metadata where retention allows.
- Frontend/user preferences, exports, and support artifacts.

### Export Procedure

1. Create an export manifest with request ID, tenant ID, data classes, owners, and destination.
2. Freeze non-essential mutations during export if consistency requires it.
3. Run approved tenant-scoped export jobs per layer.
4. Verify export completeness by counts and hashes.
5. Store export in approved encrypted storage with access expiration.
6. Notify Customer Operations when the export package is ready.

```bash
# Example manifest-driven export entrypoint; use service-owned commands where they differ.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  <approved-layer-export-command> \
    --tenant-id "<tenant-id>" \
    --request-id "<request-id>" \
    --output "s3://<approved-bucket>/<request-id>/layer3/"
```

### Deletion Procedure

1. Confirm deletion approval and retention/legal hold clearance.
2. Take or confirm a backup snapshot if policy requires reversible deletion during grace period.
3. Delete by tenant and data class using approved service entrypoints, not raw global SQL/Cypher.
4. Invalidate derived stores: caches, Neo4j projections, vector embeddings/index entries, search indexes, and generated artifacts.
5. Verify zero tenant-owned records remain in deletion scope.
6. Record deletion evidence and sign-off.

```bash
# Example tenant-scoped deletion guardrail pattern.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  <approved-layer-delete-command> \
    --tenant-id "<tenant-id>" \
    --request-id "<request-id>" \
    --confirm-tenant-scoped
```

### Tenant-Boundary Validation

```bash
# Verify no Layer 3 graph records remain for deleted tenant.
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE n.tenant_id = $tenant_id RETURN labels(n) AS labels, count(n) AS count ORDER BY labels"

# Verify no cross-tenant side effects by checking unaffected control tenant counts.
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE n.tenant_id = $control_tenant_id RETURN labels(n) AS labels, count(n) AS count ORDER BY labels"
```

Expected result for deletion: zero records for deleted tenant in approved deletion scope; unchanged counts for control tenants.

### Customer Communication

Use `docs/runbooks/customer-operations/support-escalation.md` for request tracking and `customer-incident-communication.md` only if an export/deletion problem becomes an incident. Do not expose internal record counts or infrastructure details unless approved.

### Evidence to Retain

- Request and approvals.
- Export/deletion manifest.
- Commands/jobs executed.
- Completeness or deletion validation outputs.
- Customer delivery/confirmation.
