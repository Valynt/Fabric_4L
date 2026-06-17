# Value Case Persistence — Design Note

## Goal
Replace `localStorage` and opaque `WorkspaceTabData` usage in the Value Case workflow with durable, tenant-governed backend persistence so generated business cases survive refresh, browser restart, and tenant boundaries.

## Persistence model

We extended the existing API gateway `BusinessCase` schema with a new `value_case: ValueCaseContent | None` JSONB blob. The gateway already stores `BusinessCase` records in the tenant-scoped `fabric_api_records` table via `db.business_cases` (`PostgreSQLTable` / `InMemoryTable`). Because the payload is stored opaquely as JSONB, no additional Alembic migration was required.

### `ValueCaseContent` shape

```text
{
  "inputs": { ... },                  # original generate inputs
  "selected_scenario_id": "..." | null,
  "sections": [                       # narrative / business-case sections
    { "id", "type", "title", "content", "order" }
  ],
  "assumption_ids": ["..."],          # references to L5 Assumption records
  "evidence_ids": ["..."],            # references to L2/L3 evidence
  "stakeholder_framing": [            # persona + priorities/pains/role
    { "persona", "priorities", "pains", "decision_role" }
  ],
  "claim_ids": ["..."],               # references to L5 TruthObject claims
  "roi_snapshot": { ... } | null      # captured ROI metrics
}
```

### Why the gateway JSONB table

- Tenant isolation is already enforced by the gateway's `tenant_required` dependency and `db.business_cases` tenant-scoped store.
- The frontend already talks to the gateway (`/api/v1`) via `apiGet`/`apiPost`/`apiPatch`.
- Reusing `BusinessCase` avoids creating a parallel persistence system in L4 or L5 for this focused slice.

### Backend endpoints added

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/accounts/{account_id}/value-cases` | List cases for an account |
| GET | `/v1/accounts/{account_id}/value-cases/{value_case_id}` | Get a specific case |
| POST | `/v1/accounts/{account_id}/value-case` | Create a new case |
| PATCH | `/v1/accounts/{account_id}/value-cases/{value_case_id}` | Update editable fields |
| POST | `/v1/accounts/{account_id}/value-cases/{value_case_id}/publish` | Publish a draft case |

## Frontend integration

- `useValueCaseArtifacts` now loads from `GET /accounts/{accountId}/value-cases` and saves via the endpoints above.
- `localStorage` is no longer the source of truth for durable case data; only transient UI state (e.g. selected version id) may live in React state.
- `ValueCasePage` uses the new hook surface, adds a Publish action, and surfaces load/generate/publish errors.

## Intentionally deferred fields

The following Value Evidence Graph (VEG) fields are **not** duplicated inside `ValueCaseContent`. They are referenced by stable identifier and resolved through their canonical layers when needed:

- Full assumption metadata → L5 `Assumption` objects (referenced by `assumption_ids`).
- Full evidence metadata → L2/L3 evidence records (referenced by `evidence_ids`).
- Full claim/TruthObject metadata → L5 `TruthObject` records (referenced by `claim_ids`).
- Real-time graph relationships (e.g. evidence → claim → value driver edges) → L3 graph queries.
- ROI scenario lineage and version history → L3 ROI calculator / scenario store.

The `roi_snapshot` field captures a point-in-time snapshot of metrics for the artifact, but it does not replace the authoritative ROI calculation record.

## Migration notes

- No database migration is required; the change is additive to the existing JSONB payload.
- Existing `BusinessCase` records without `value_case` continue to deserialize with `value_case=None`.
- Frontend `.env.example` gained `VITE_API_ROUTE_PREFIX=` (empty default) so the new `"api"` client layer can target the gateway.
