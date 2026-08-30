# Rebuild Neo4j Projection Runbook

## Purpose

Use this runbook when a Neo4j graph projection, tenant-scoped read model, relationship expansion, or graph-derived cache is stale, incomplete, or suspected corrupt while the canonical source data is still intact. This is a **derived-store rebuild** procedure: do not treat Neo4j as the source of truth until the source-of-truth checks below pass.

## Trigger

Projection integrity/retrieval alerts, missing tenant ownership, source/projection drift, or an approved rebuild request.

## Severity

SEV1 for cross-tenant or broad integrity risk; SEV2 for production retrieval impact; SEV3 for bounded degradation with source data intact.

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

- `tenant-isolation-gate`; Layer 3 tests and contract checks; observability alert gates; `gate-backup-restore-readiness`; production-readiness gate.

## Related Runbooks

- ./rebuild-vector-index.md, ../neo4j-backup-restore.md, ../data-governance/investigate-data-corruption.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Layer 3 Knowledge Graph derived Neo4j projections and read models.  
> **Primary owners:** `vf-db-oncall`, Layer 3 owner, Security for tenant-boundary concerns.  
> **Related runbooks:** `docs/troubleshooting/runbooks/infrastructure/neo4j-down.md`, `docs/troubleshooting/runbooks/infrastructure/neo4j-unreachable.md`, `docs/runbooks/neo4j-backup-restore.md`.

### Purpose

Use this runbook when a Neo4j graph projection, tenant-scoped read model, relationship expansion, or graph-derived cache is stale, incomplete, or suspected corrupt while the canonical source data is still intact. This is a **derived-store rebuild** procedure: do not treat Neo4j as the source of truth until the source-of-truth checks below pass.

### Triggers

- Layer 3 graph queries return missing or obviously stale entities or relationships.
- Layer 4 agents receive inconsistent graph context for value-tree projection or semantic matching.
- Neo4j recovered from outage, restore, or compaction and needs projection refresh.
- Tenant-scoped graph counts diverge from canonical ingestion/extraction records.
- Post-deploy validation detects missing tenant indexes, labels, or relationship projections.

### Safety Principles

1. **Confirm source of truth first.** Canonical records come from the upstream ingestion/extraction repositories, contracts, and tenant-owned source documents; Neo4j projections are rebuildable derived state.
2. **Rebuild by tenant or bounded shard first.** Avoid global rebuilds unless the incident commander approves the blast radius.
3. **Preserve tenant boundaries.** Every read, delete, merge, and validation query must include `tenant_id`; never use request-body tenant IDs over authenticated context.
4. **Write to a shadow projection when possible.** Prefer `projection_version` or a temporary label/property before cutting traffic over.
5. **Keep an audit trail.** Record operator, tenant IDs, source snapshot, projection version, Cypher/scripts executed, and validation evidence.

### Preconditions

- Incident commander assigned for SEV1/SEV2 or customer-visible rebuilds.
- Affected tenant IDs and graph labels are identified.
- Latest backups/snapshots are confirmed available if destructive cleanup is needed.
- Layer 3 write traffic can be paused, rate-limited, or routed to a read-only mode for affected tenants.
- You have credentials for Kubernetes, Neo4j, and source-of-truth stores.

### Source-of-Truth Confirmation

Before rebuilding, confirm the canonical input is trustworthy.

```bash
# Confirm Layer 3 API health and dependency state.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  curl -fsS http://localhost:8000/health | jq

# Confirm Neo4j is reachable before planning an in-place rebuild.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  nc -zv neo4j 7687

# Capture existing graph counts by tenant and label for the affected scope.
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE n.tenant_id IN $TENANT_IDS RETURN n.tenant_id AS tenant_id, labels(n) AS labels, count(*) AS count ORDER BY tenant_id, labels"
```

Confirm with the Layer 1/Layer 2 owners that source documents, extraction events, provenance metadata, and contract payloads for the affected tenants are complete and not also corrupt. If source data is corrupt, stop here and use `docs/runbooks/data-governance/investigate-data-corruption.md`.

### Containment

1. Announce rebuild scope in `#incident-response` and `#vf-db-oncall`.
2. Pause non-critical graph mutations for the affected tenant(s):

   ```bash
   kubectl set env deployment/layer3-knowledge -n value-fabric \
     L3_GRAPH_WRITE_FREEZE_TENANTS="$TENANT_IDS"
   kubectl rollout restart deployment/layer3-knowledge -n value-fabric
   ```

3. If Layer 4 workflows depend on the stale projection, pause or drain only those workflows:

   ```bash
   kubectl exec -n value-fabric deployment/layer4-agents -- \
     curl -X POST http://localhost:8000/api/v1/workflows/pause \
     -H "Content-Type: application/json" \
     -d '{"reason":"neo4j_projection_rebuild","tenant_ids":["<tenant-id>"]}'
   ```

4. For customer-visible incidents, use `docs/runbooks/customer-operations/customer-incident-communication.md`.

### Rebuild Procedure

#### 1. Create a rebuild manifest

Create an incident-local manifest with:

- Incident ID and operator.
- Tenant IDs and graph labels in scope.
- Source snapshot timestamp or extraction batch IDs.
- Current `projection_version` and target `projection_version`.
- Commands/scripts to run and expected counts.

#### 2. Validate schema and tenant indexes

```bash
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state RETURN name, type, labelsOrTypes, properties, state ORDER BY name"
```

Required tenant filters include `tenant_id` indexes for affected labels. Required vector indexes are covered in `docs/runbooks/reliability/rebuild-vector-index.md`.

#### 3. Rebuild into a shadow projection when possible

Prefer an additive rebuild that marks new nodes/relationships with a target projection version:

```bash
export TARGET_PROJECTION_VERSION="incident-<id>-$(date -u +%Y%m%d%H%M%S)"

# Run the approved projection rebuild entrypoint for the affected tenant scope.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  <approved-layer3-projection-rebuild-command> \
    --tenant-ids "$TENANT_IDS" \
    --projection-version "$TARGET_PROJECTION_VERSION" \
    --source-snapshot "$SOURCE_SNAPSHOT" \
    --mode shadow
```

If no shadow path exists, stop and get Layer 3 owner approval before any destructive cleanup. In-place rebuilds must delete only rows that match the affected tenant and projection labels.

#### 4. Derived-store rebuild safety for in-place cleanup

Only run in-place cleanup after approval and backup confirmation:

```cypher
// Example pattern; adapt labels and relationship types to the approved manifest.
MATCH (n:Capability)
WHERE n.tenant_id = $tenant_id AND n.projection_version = $old_projection_version
DETACH DELETE n;
```

Never run unscoped `MATCH (n) DETACH DELETE n`, relationship deletes without `tenant_id`, or cross-tenant merge logic. If the rebuild script cannot prove tenant scoping, do not run it.

#### 5. Cut over to the rebuilt projection

```bash
kubectl set env deployment/layer3-knowledge -n value-fabric \
  L3_ACTIVE_PROJECTION_VERSION="$TARGET_PROJECTION_VERSION"
kubectl rollout restart deployment/layer3-knowledge -n value-fabric
```

If projection versioning is not enabled, cutover is the successful completion of the tenant-scoped in-place rebuild plus validation below.

### Tenant-Boundary Validation

Run these checks for every affected tenant and at least one unaffected tenant.

```bash
# No nodes in affected labels may have missing tenant_id.
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE any(label IN labels(n) WHERE label IN $LABELS) AND (n.tenant_id IS NULL OR n.tenant_id = '') RETURN labels(n) AS labels, count(n) AS missing_tenant"

# Relationships must not cross tenants unless explicitly modeled and approved.
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (a)-[r]->(b) WHERE a.tenant_id IS NOT NULL AND b.tenant_id IS NOT NULL AND a.tenant_id <> b.tenant_id RETURN type(r) AS rel_type, count(r) AS cross_tenant_edges LIMIT 20"

# Tenant A query must not return Tenant B IDs.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  curl -fsS "http://localhost:8000/api/v1/graph/entities?tenant_id=<tenant-a>&limit=50" \
  -H "Authorization: Bearer $TENANT_A_TOKEN" | jq
```

Expected result: missing-tenant count is zero, cross-tenant edge count is zero unless pre-approved shared reference data is documented, and hostile cross-tenant reads fail closed.

### Post-Rebuild Quality Checks

- Compare rebuilt node and relationship counts against the source manifest by tenant and label.
- Sample high-value entities and verify name, description, provenance, confidence, and source document IDs.
- Run a Layer 3 query smoke for graph visualization, knowledge retrieval, value tree traversal, and entity search.
- Resume one paused Layer 4 workflow and verify it receives graph context from the target projection.
- Monitor Layer 3 error rate, Neo4j CPU/memory, query latency, and graph query result volume for at least 30 minutes.

```bash
kubectl logs -n value-fabric -l app=layer3-knowledge --since=30m | \
  grep -E "projection|tenant|Neo4jError|ServiceUnavailable|cross_tenant" || true

kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE n.projection_version = $projection_version RETURN labels(n) AS labels, n.tenant_id AS tenant_id, count(*) AS count ORDER BY tenant_id, labels"
```

### Rollback

- Shadow rebuild: restore `L3_ACTIVE_PROJECTION_VERSION` to the prior version and restart Layer 3.
- In-place rebuild: restore from snapshot or rerun projection from the last known-good source snapshot.
- Keep Layer 4 workflows paused until tenant-boundary and quality checks pass.

### Escalation

- Page `vf-db-oncall` if Neo4j becomes unavailable or restore is required.
- Page Security immediately for any confirmed cross-tenant projection leakage.
- Page Layer 3 owner if the rebuild entrypoint is missing tenant scoping or source counts do not reconcile.

### Evidence to Retain

- Rebuild manifest and approvals.
- Source-of-truth confirmation output.
- Backup/snapshot ID.
- Cypher/script logs.
- Tenant-boundary validation output.
- Post-rebuild quality-check results.
