# Customer Data Export or Deletion Runbook

> **Scope:** Customer data subject export, deletion, tenant offboarding, and evidence retention coordination across Value Fabric layers.  
> **Primary owners:** Customer Operations, Data Governance, Security, service owners for affected layers.

## Purpose

Use this runbook for approved customer requests to export or delete tenant-owned data. This is a governed operation: never run ad hoc unscoped queries, never delete shared reference data, and never bypass legal hold or retention requirements.

## Intake Requirements

- Request ID and requesting customer/tenant.
- Verified requester identity and authority.
- Operation type: export, deletion, or both.
- Tenant ID(s), environment, and product area.
- Deadline, contractual/regulatory driver, and approval from Data Governance.
- Legal hold, security investigation, billing, or audit retention constraints.

## Approval Gates

| Gate | Owner | Required before action |
|---|---|---|
| Identity and authorization | Customer Operations | Requester is verified tenant admin or approved legal contact. |
| Scope | Data Governance | Tenant IDs and data classes are approved. |
| Retention/legal hold | Legal/Security | No deletion conflict or approved exception documented. |
| Technical plan | Service owners | Export/delete plan covers all layers and derived stores. |

## Data Map Checklist

Include tenant-owned data in:

- Layer 1 ingestion jobs, crawl artifacts, source documents, and provenance.
- Layer 2 extraction events, entities, RDF/OWL outputs, and provenance.
- Layer 3 graph nodes/relationships, evidence, embeddings, vector indexes, and caches.
- Layer 4 workflow state, checkpoints, prompts, tool traces, and generated business cases.
- Layer 5 TruthObjects, claim validation, and maturity evidence.
- Layer 6 tenant benchmark usage, peer-comparison outputs, and reports.
- API gateway auth/audit metadata where retention allows.
- Frontend/user preferences, exports, and support artifacts.

## Export Procedure

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

## Deletion Procedure

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

## Tenant-Boundary Validation

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

## Customer Communication

Use `docs/runbooks/customer-operations/support-escalation.md` for request tracking and `customer-incident-communication.md` only if an export/deletion problem becomes an incident. Do not expose internal record counts or infrastructure details unless approved.

## Evidence to Retain

- Request and approvals.
- Export/deletion manifest.
- Commands/jobs executed.
- Completeness or deletion validation outputs.
- Customer delivery/confirmation.
