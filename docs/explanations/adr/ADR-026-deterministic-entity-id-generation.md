# ADR-026: Deterministic Entity ID Generation for Layer 2 Extraction

## Status
Accepted

## Context
Layer 2 extraction produces entities and relationships that are consumed by downstream layers (L3 knowledge graph, L4 agents). For stable graph operations and agent reasoning, entities must have stable, reproducible identifiers across idempotent re-runs of the extraction pipeline.

Without deterministic IDs:
- Re-running extraction on the same source creates duplicate entities
- Graph deduplication becomes expensive and error-prone
- Agent reasoning cannot reliably track entity identity over time
- Audit trails become fragmented

## Decision
Layer 2 will use deterministic ID generation based on a canonical entity signature computed from identity-defining fields.

### ID Generation Formula

```
deterministic_id = SHA256(
    tenant_id + "|" + 
    source_url + "|" + 
    entity_type + "|" + 
    entity_signature + "|" + 
    extraction_version
)
```

### Entity Signature Construction

The entity signature includes only fields that define *what* the entity is, excluding extraction metadata (confidence, timestamps, IDs).

**Capability:** `entity_type|name|description|sorted(technical_features)`
**UseCase:** `entity_type|name|description|sorted(industry_context)`
**Persona:** `entity_type|role_type|title|department`
**ValueDriver:** `entity_type|category|name|description|unit`
**Feature:** `entity_type|name|description`
**ValueMetric:** `entity_type|name|description|unit|direction`
**Relationship:** `entity_type|source_entity_id|target_entity_id|predicate_type`

### Normalization Rules

- Text: lowercase, strip whitespace, collapse internal spaces
- Lists: sort alphabetically, deduplicate
- Enums: use string value
- None/empty: convert to empty string

### Extraction Version

The `extraction_version` parameter allows ID evolution when extraction logic changes:
- `v1`: Initial extraction implementation
- `v2`: New entity types or signature changes
- Increment when entity signature structure changes

## Consequences

### Positive
- Same source produces same entity IDs across re-runs
- Tenant isolation is enforced (different tenant = different ID)
- Extraction versioning allows controlled ID evolution
- Graph deduplication becomes trivial (same ID = same entity)
- Agent reasoning can track entity identity reliably

### Negative
- Changing extraction version creates new IDs for existing entities
- Requires migration strategy when extraction_version changes
- Entity signature changes require version bump

### Mitigations
- Document extraction version changes in changelog
- Provide migration tooling for version transitions
- Keep extraction_version stable unless necessary
- Consider backward-compatible signature changes when possible

## Implementation

The implementation is in `services/layer2-extraction/src/layer2_extraction/extraction/entity_id.py`:

- `compute_deterministic_id()`: Main ID generation function
- `_build_entity_signature()`: Canonical signature construction
- `_normalize_text()`: Text normalization for stability

Tests are in `services/layer2-extraction/tests/test_deterministic_ids.py`:

- ID stability across re-runs
- ID changes with tenant/source/version
- Signature normalization (case, whitespace, ordering)
- ID uniqueness for different entities

## References
- Layer 2 Remediation Roadmap: P1-2 Deterministic Stable Entity IDs
- `services/layer2-extraction/src/layer2_extraction/extraction/entity_id.py`
- `services/layer2-extraction/tests/test_deterministic_ids.py`
