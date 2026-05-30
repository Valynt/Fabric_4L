# Investigate Data Corruption Runbook

> **Scope:** Suspected corruption in source records, graph projections, embeddings, workflow state, validation outputs, or customer-visible generated artifacts.  
> **Primary owners:** Data Governance, affected service owner, Security if tenant boundaries or data exposure are suspected.

## Purpose

Use this runbook when data is missing, duplicated, stale, overwritten, incorrectly tenant-scoped, or inconsistent across layers. The goal is to identify the canonical source of truth, contain customer impact, and repair derived stores safely.

## Severity

| Severity | Condition |
|---|---|
| SEV1 | Cross-tenant data exposure, destructive overwrite, or customer decisions based on materially corrupt data. |
| SEV2 | Single-tenant data corruption with visible product impact. |
| SEV3 | Internal inconsistency or derived-store drift with no customer-visible impact. |

## Immediate Containment

1. Freeze affected writes, workflows, or tenants at the smallest safe scope.
2. Preserve logs, source records, workflow traces, checkpoints, and generated outputs.
3. If tenant leakage is possible, page Security and treat as SEV1 until disproven.
4. Stop rebuilds or migrations that may be spreading corruption.

```bash
kubectl set env deployment/layer3-knowledge -n value-fabric \
  L3_GRAPH_WRITE_FREEZE_TENANTS="<tenant-id>"
kubectl rollout restart deployment/layer3-knowledge -n value-fabric
```

## Source-of-Truth Analysis

For the affected data object, identify the canonical owner:

| Data class | Likely source of truth |
|---|---|
| Source document/crawl artifact | Layer 1 ingestion storage and provenance. |
| Extracted entity or ontology mapping | Layer 2 extraction output plus source document provenance. |
| Graph relationship/projection | Derived Layer 3 Neo4j projection from Layer 2/source records. |
| Embedding/vector result | Derived Layer 3 embedding from tenant-owned text. |
| Agent workflow state/output | Layer 4 checkpoint, trace, prompt/tool versions, and upstream context. |
| Validated claim | Layer 5 TruthObject and evidence references. |
| Benchmark comparison | Layer 6 dataset lineage and tenant usage record. |

Do not repair derived stores until the canonical owner confirms whether its source records are valid.

## Investigation Steps

```bash
# Gather recent errors across likely affected layers.
kubectl logs -n value-fabric -l app=layer3-knowledge --since=4h | \
  grep -Ei "corrupt|tenant|projection|embedding|constraint|duplicate|mismatch" || true

kubectl logs -n value-fabric -l app=layer4-agents --since=4h | \
  grep -Ei "checkpoint|business_case|truth|evidence|tenant|schema" || true

# Check graph records for missing tenant ownership.
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE n.tenant_id IS NULL OR n.tenant_id = '' RETURN labels(n) AS labels, count(n) AS missing_tenant ORDER BY missing_tenant DESC LIMIT 20"
```

Check for:

- Recent deploys, migrations, backfills, imports, or manual repair jobs.
- Contract/schema drift between source payload and consumer.
- Missing or inconsistent `tenant_id` fields.
- Duplicate IDs within a tenant or shared IDs across tenants.
- Derived-store lag after source updates.
- Failed retries that partially wrote records.

## Repair Decision Matrix

| Root cause | Repair path |
|---|---|
| Canonical source is corrupt | Restore/reprocess source data first; do not rebuild derived stores from bad source. |
| Neo4j projection is stale/corrupt | Use `docs/runbooks/reliability/rebuild-neo4j-projection.md`. |
| Vector embeddings/index are stale/corrupt | Use `docs/runbooks/reliability/rebuild-vector-index.md`. |
| Workflow checkpoint replay caused bad output | Cancel/restart from clean state and validate generated artifacts. |
| Contract drift | Fix contract alignment, add regression tests, and replay affected records. |
| Tenant leak | Security-led incident; preserve evidence and stop all repair that could erase forensic data. |

## Validation

- Canonical counts reconcile to repaired stores by tenant and data class.
- Tenant-boundary hostile checks pass.
- Customer-visible artifacts are regenerated or marked invalid.
- Logs show no continuing corruption signatures.
- A control tenant remains unchanged.

## Customer Communication

Engage Customer Operations if customer-visible data may be wrong. Communications should state facts, affected product area, mitigation, and next update; avoid speculation about root cause until confirmed.

## Post-Incident

- Add regression tests for the failure mode.
- Add monitoring for the drift/corruption signal.
- Record affected tenants, records, source snapshot, repair commands, and validation evidence.
