# Layer 3 Graph Field Cutover (name/entity_type/confidence_score)

## Legacy compatibility inventory

Layer 3 `GraphNode` currently supports deprecated aliases for compatibility:
- `label` -> canonical `name`
- `type` -> canonical `entity_type`
- `confidence` -> canonical `confidence_score`

Mirrored model locations:
- `value_fabric/layer3/api/models.py`
- `services/layer3-knowledge/src/api/models.py`

## Consumer inventory (May 12, 2026)

Graph payload consumers were checked for legacy graph fields in UI and service callers.

Active canonical consumers:
- `apps/web/src/lib/schemas.ts` (`GraphNodeSchema` uses `name`, `entity_type`, `confidence_score`)
- `value_fabric/layer3/api/routes/query_search.py` (`confidence_score` and `entity_type` response fields)
- contract tests under `tests/contract/` validating canonical fields

Legacy compatibility coverage remains in model serialization only, to avoid breaking older clients.

## Versioned deprecation schedule

| Phase | Version window | Dates | Contract behavior |
|---|---|---|---|
| Current | `<= v2.3` | through **2026-06-30** | Emit canonical fields and deprecated aliases. |
| Warning | `v2.4` | **2026-07-01** through **2026-09-30** | Keep aliases deprecated; monitor usage and emit deprecation metadata. |
| Removal | `>= v2.5` | starting **2026-10-01** | Remove aliases from response contracts. Canonical fields only. |

## Cutover policy

- Canonical response shape (effective now): `id`, `name`, `entity_type`, `confidence_score`, `properties`.
- Deprecated aliases (`label`, `type`, `confidence`):
  - still emitted in `GraphNode.model_dump()` for one release window.
  - accepted as input only when canonical fields are absent, or values are identical.
  - conflicting canonical+deprecated values are rejected with validation error.
- Removal target:
  - remove alias emission and input acceptance in release `v2.5` (target date: **2026-10-01**).
  - OpenAPI now carries explicit deprecation metadata on each alias:
    - `deprecated: true`
    - `x-deprecation-target-version: v2.5`
    - `x-deprecation-target-date: 2026-10-01`

GraphEdge compatibility alias:
- `relationship_type` -> canonical `type`
- marked deprecated with the same `v2.5 / 2026-10-01` removal target.

## Migration guidance

API consumers should:
1. Read only `name`, `entity_type`, and `confidence_score`.
2. For edges, read only `type` (do not read `relationship_type`).
3. Stop writing `label`, `type`, `confidence`, and `relationship_type` alias payload fields.
4. Treat alias fields as temporary compatibility fields until removed in `v2.5` (2026-10-01).
