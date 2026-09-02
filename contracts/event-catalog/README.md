# Event Catalog

The event catalog is the semantic source of truth for event types produced and
consumed across the Value Fabric platform. It is statically validated by
`scripts/ci/validate-event-catalog.py` on every PR (`validate-event-catalog.py
--strict`), so catalog drift cannot pass CI.

## Layout

| Path | Purpose |
|---|---|
| `registry.yaml` | Canonical event registry (all domains merged). |
| `domains/*.yaml` | Per-domain event entries (`billing`, `identity`, `knowledge`, `agents`). |
| `consumers/*.yaml` | Declared consumer subscriptions per bounded context. |
| `event-entry.schema.json` | JSON Schema for a single catalog entry. |
| `generated/` | Regenerated artifacts (`ownership-matrix.json`, `producer-consumer-graph.json`). |

## `tenant_scope`

Every catalog entry carries a `tenant_scope` from the canonical four-value
enum (also used by tool `tenant_scope` in the agent registry and the Layer 4
OpenAPI `x-tenant-scope` extension):

- `TENANT` — event is scoped to a single tenant.
- `TENANT_AND_BILLING_ACCOUNT` — event may be scoped to a billing account in
  addition to a tenant.
- `GLOBAL` — event is not tenant-scoped.
- `SYSTEM` — event is platform/system level.

## Payload Schema Hard Gate

Rule 2 requires every entry's `schema_ref` to resolve to a committed payload
schema. `schema_ref` uses the URI-like form `jsonschema://<path>@<version>`,
which maps to a file under `contracts/jsonschema/<path>@<version>.schema.json`
(for example `jsonschema://billing/events/billing-account-created@1.0.0` →
`contracts/jsonschema/billing/events/billing-account-created@1.0.0.schema.json`).

The validator converts the reference, strips the `@version` suffix as a
fallback, and requires the resolved path to exist in
`contracts/schema-index.json`. A missing payload schema is a blocking
`Violation("2")` — the hard gate cannot be deferred. Any new event or schema
change must ship its payload schema and schema-index entry in the same change
set. `sensitive_payload` entries must not include examples (rule 8).