# Rebuild Vector Index Runbook

## Purpose

Use this runbook when semantic search, entity resolution, evidence retrieval, or agent context selection is degraded because vector indexes are missing, stale, dimension-mismatched, or built from incorrect embeddings. Vector indexes and embeddings are **derived stores**: they must be rebuilt from canonical source content and tenant-scoped graph records, not from untrusted query results.

## Trigger

Vector index failure/population alerts, retrieval-quality regression, embedding drift, or an approved rebuild request.

## Severity

SEV1 for cross-tenant retrieval or broad integrity risk; SEV2 for production semantic-search impact; SEV3 for bounded degradation with source data intact.

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

- `tenant-isolation-gate`; Layer 3 tests and contract checks; agent evaluation/retrieval eval gates; observability alert gates; production-readiness gate.

## Related Runbooks

- ./rebuild-neo4j-projection.md, ../data-governance/investigate-data-corruption.md, ../agents/investigate-hallucinated-business-case.md

## Post-Incident Follow-Up

Assign owners and due dates for the root-cause record, corrective tests/alerts/gates, control improvements, customer follow-up, and any required update to this runbook.

## Procedure Details

> **Scope:** Layer 3 Neo4j vector indexes and embedding-backed retrieval.  
> **Primary owners:** Layer 3 owner, `vf-db-oncall`, AI platform owner.  
> **Related runbooks:** `docs/runbooks/reliability/rebuild-neo4j-projection.md`, `docs/troubleshooting/runbooks/application/llm-provider-outage.md`, `docs/troubleshooting/runbooks/application/llm-cost-anomaly.md`.

### Purpose

Use this runbook when semantic search, entity resolution, evidence retrieval, or agent context selection is degraded because vector indexes are missing, stale, dimension-mismatched, or built from incorrect embeddings. Vector indexes and embeddings are **derived stores**: they must be rebuilt from canonical source content and tenant-scoped graph records, not from untrusted query results.

### Canonical Indexes

Layer 3 defines vector indexes for the current retrieval entities:

- `capability_embedding_idx` on `Capability.embedding`
- `usecase_embedding_idx` on `UseCase.embedding`
- `persona_embedding_idx` on `Persona.embedding`
- `valuedriver_embedding_idx` on `ValueDriver.embedding`
- `evidence_embedding_idx` on `Evidence.embedding`

Confirm the active embedding dimension from Layer 3 settings before rebuilding. A dimension mismatch between the configured index and the embedding adapter must fail closed.

### Triggers

- `SHOW INDEXES` reports vector index `FAILED`, `POPULATING` for too long, or missing.
- Semantic search returns no results despite known matching source records.
- Layer 4 agent evidence/context quality drops after an embedding model or dimension change.
- Logs include vector dimension mismatch, embedding provider unavailable, or `db.index.vector.queryNodes` errors.
- A source-document reprocessing incident requires embeddings to be refreshed.

### Safety Principles

1. **Confirm source-of-truth content.** Rebuild embeddings from canonical source text, entity descriptions, and evidence content; do not embed generated answers or customer-visible summaries.
2. **Preserve tenant isolation.** Re-embedding jobs, cache invalidation, and retrieval validation must include `tenant_id`.
3. **Avoid global destructive drops.** Recreate indexes only when needed; re-embed by tenant/batch and keep old embeddings until validation passes where possible.
4. **Control LLM/embedding spend.** Use approved model routing, cost budgets, and rate limits.
5. **Record model lineage.** Store embedding model name, dimension, batch ID, and source snapshot.

### Preconditions

- Confirm the embedding provider is healthy or select an approved fallback.
- Confirm the intended embedding model and dimension match runtime settings.
- Confirm source content and graph entities are trustworthy; if graph projection is corrupt, run `rebuild-neo4j-projection.md` first.
- Freeze affected tenant semantic search traffic or notify Customer Operations if customer-visible.

### Diagnosis

```bash
# Check Layer 3 health.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  curl -fsS http://localhost:8000/health | jq

# Inspect vector index state.
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state, populationPercent, failureMessage WHERE type = 'VECTOR' RETURN * ORDER BY name"

# Check recent embedding/vector errors.
kubectl logs -n value-fabric -l app=layer3-knowledge --since=2h | \
  grep -Ei "embedding|vector|dimension|queryNodes|provider" || true
```

### Source-of-Truth Confirmation

For each tenant and label in scope:

1. Confirm canonical source records exist and are complete.
2. Confirm each record has a stable `id`, `tenant_id`, source/provenance pointer, and text field used for embedding.
3. Confirm no upstream extraction or data-corruption incident is still active.
4. Capture pre-rebuild counts:

```bash
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE any(label IN labels(n) WHERE label IN $LABELS) AND n.tenant_id IN $TENANT_IDS RETURN n.tenant_id AS tenant_id, labels(n) AS labels, count(n) AS total, count(n.embedding) AS with_embedding ORDER BY tenant_id, labels"
```

### Containment

- If retrieval quality is customer-visible, publish an internal incident update and pause affected agent workflows.
- Disable semantic retrieval for affected tenants only if lexical/graph fallback is safer:

```bash
kubectl set env deployment/layer3-knowledge -n value-fabric \
  L3_SEMANTIC_SEARCH_DISABLED_TENANTS="$TENANT_IDS"
kubectl rollout restart deployment/layer3-knowledge -n value-fabric
```

- If the issue is provider outage or rate limiting, follow `docs/runbooks/agents/llm-provider-outage.md` before triggering a rebuild.

### Rebuild Procedure

#### 1. Generate a rebuild manifest

Include tenant IDs, labels, index names, embedding model, configured dimension, source snapshot, cost budget, batch size, and rollback plan.

#### 2. Re-embed affected records in bounded batches

```bash
export EMBEDDING_REBUILD_ID="incident-<id>-$(date -u +%Y%m%d%H%M%S)"

kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  <approved-layer3-reembedding-command> \
    --tenant-ids "$TENANT_IDS" \
    --labels "$LABELS" \
    --mode reembed \
    --embedding-rebuild-id "$EMBEDDING_REBUILD_ID" \
    --source-snapshot "$SOURCE_SNAPSHOT" \
    --batch-size 100
```

If the approved rebuild command differs, use the canonical Layer 3 entrypoint documented by the service owner. Do not write an ad hoc script that omits tenant filters.

#### 3. Recreate failed vector indexes only when necessary

If indexes are missing or failed, recreate only the affected index names:

```cypher
DROP INDEX capability_embedding_idx IF EXISTS;
CREATE VECTOR INDEX capability_embedding_idx IF NOT EXISTS
FOR (n:Capability) ON (n.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};
```

Use the active configured dimension rather than copying `384` blindly. Repeat for only the approved index names in the manifest. Do not drop tenant B-tree indexes.

#### 4. Wait for population to complete

```bash
watch -n 30 'kubectl exec -n value-fabric deployment/neo4j -- cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "SHOW INDEXES YIELD name, type, state, populationPercent WHERE type = '\''VECTOR'\'' RETURN name, state, populationPercent ORDER BY name"'
```

Proceed only when affected indexes are `ONLINE`.

### Tenant-Boundary Validation

```bash
# Embeddings must remain tenant-owned.
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE n.embedding IS NOT NULL AND (n.tenant_id IS NULL OR n.tenant_id = '') RETURN labels(n) AS labels, count(n) AS missing_tenant"

# Vector retrieval must filter by authenticated tenant.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  curl -fsS "<approved-layer3-semantic-search-url>?q=<known-query>" \
  -H "Authorization: Bearer $TENANT_A_TOKEN" | jq

# Run a hostile Tenant A query for a Tenant B-only fixture and confirm zero Tenant B IDs are returned.
kubectl exec -n value-fabric deployment/layer3-knowledge -- \
  curl -fsS "<approved-layer3-semantic-search-url>?q=<tenant-b-only-term>" \
  -H "Authorization: Bearer $TENANT_A_TOKEN" | jq '.results[].tenant_id' | sort -u
```

Expected result: no embeddings without tenant ownership, no cross-tenant semantic results, and all vector retrieval paths include tenant filters.

### Post-Rebuild Quality Checks

- Compare pre/post `with_embedding` counts by tenant and label.
- Query known golden fixtures for each affected label and confirm expected top-k results.
- Verify evidence retrieval returns sources with provenance and confidence metadata.
- Verify Layer 4 business-case and value-tree workflows cite the rebuilt evidence rather than stale context.
- Monitor cost metrics and embedding latency for at least 30 minutes.

```bash
kubectl exec -n value-fabric deployment/neo4j -- \
  cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "MATCH (n) WHERE n.embedding_rebuild_id = $embedding_rebuild_id RETURN n.tenant_id AS tenant_id, labels(n) AS labels, count(*) AS embedded ORDER BY tenant_id, labels"

kubectl logs -n value-fabric -l app=layer3-knowledge --since=30m | \
  grep -Ei "semantic_search|vector|embedding|cross_tenant|dimension" || true
```

### Rollback

- Restore previous embedding fields from snapshot if the new vectors fail validation.
- Re-enable lexical/graph-only fallback while re-embedding is retried.
- Restore index definitions from Layer 3 schema if a manual Cypher command used the wrong dimension.

### Escalation

- Page AI platform owner for provider/model/dimension mismatch.
- Page `vf-db-oncall` for failed Neo4j index population.
- Page Security for any cross-tenant vector retrieval result.
- Page FinOps if rebuild spend exceeds the approved budget.

### Evidence to Retain

- Rebuild manifest, source snapshot, embedding model/dimension, and batch IDs.
- `SHOW INDEXES` output before and after rebuild.
- Tenant-boundary validation results.
- Golden query quality checks and affected customer verification.
