# Layer 5 API Compatibility Policy

This policy defines how Layer 5 (Ground Truth) API changes must be classified, implemented, validated, and documented during Phase 3 enhancements.

## Scope

Applies to all contract-impacting Layer 5 API changes, including:

- `services/layer5-ground-truth/src/layer5_ground_truth/api/`
- `contracts/openapi/layer5-ground-truth.json`
- `contracts/jsonschema/` artifacts used by Layer 5 payloads
- Generated clients and downstream consumers (especially Layer 4 and Layer 6 integrations)

## 1) Compatibility Classification

Every Phase 3 enhancement ticket must include one classification for each API change.

### Additive-safe changes

A change is additive-safe only when existing clients can continue operating without code changes and without behavioral ambiguity.

Allowed additive-safe examples:

- Adding optional response fields with stable defaults/omission semantics.
- Adding optional request fields that are not required for existing behavior.
- Adding new enum values **only** when all known consumers treat unknown values safely.
- Adding new non-default endpoints that do not alter existing route behavior.
- Adding metadata blocks that consumers may ignore without breaking parsing.

### Breaking changes

A change is breaking if any existing consumer may fail, mis-parse, or change behavior unexpectedly.

Breaking examples (non-exhaustive):

- Removing or renaming fields, routes, or query parameters.
- Changing field type, format, cardinality, or nullability.
- Making previously optional request fields required.
- Changing response envelope shape or error schema.
- Changing sorting, pagination, filtering, or idempotency semantics in ways clients depend on.
- Introducing enum narrowing or behavior that causes existing client assumptions to fail.

## 2) Versioned Routes vs Additive Fields

Use this decision rule:

- Use additive fields on existing routes only when the change is strictly additive-safe.
- Introduce versioned routes (or a major contract version) for any breaking change.

### Route versioning is required when:

- Any request/response contract is breaking.
- Existing parsers in Layer 4 or Layer 6 cannot be guaranteed to tolerate the new shape.
- Semantics change in a way that could alter business meaning (validation truth status, evidence interpretation, maturity ladder logic).

### Additive extension on existing route is allowed when:

- New data is optional and backward-compatible.
- Existing clients receive the same required fields and semantics.
- Consumer-impact assessment confirms no parse/runtime breakage.

## 3) Required update steps for frontend and generated clients

For every Layer 5 contract-impacting change, complete all applicable items:

1. Update Layer 5 OpenAPI source-of-truth (`contracts/openapi/layer5-ground-truth.json`).
2. Update/add JSON Schema artifacts in `contracts/jsonschema/` if payload schemas changed.
3. Regenerate client artifacts used by frontend and other typed consumers.
4. Update frontend API types/hooks/consumers for any newly exposed fields or versioned endpoints.
5. Verify old-version consumers remain functional (for additive changes) or migrate to new version (for breaking changes).
6. Document migration/deprecation expectations when versioning is introduced.

## 4) Required Layer 4 / Layer 6 integration test updates

Any Layer 5 contract-impacting change must update integration tests that validate cross-layer payload expectations.

Minimum required coverage:

- Layer 4 integration paths that consume Layer 5 truth outputs.
- Layer 6 integration paths that consume Layer 5 validation/benchmark-relevant outputs.
- Negative/parser robustness tests for unknown additive fields and version-mismatch scenarios.
- Regression tests for prior contract behavior still promised as compatible.

If tests cannot be updated in the same PR, the PR must be blocked until linked follow-up work is approved by maintainers.

## 5) Phase 3 enhancement ticket requirements (mandatory)

Each Phase 3 enhancement ticket must include:

- **Compatibility classification:** additive-safe or breaking (with justification).
- **Consumer impact assessment:** explicit list of impacted consumers (frontend, Layer 4, Layer 6, external clients) and expected changes.
- **Rollback behavior if downstream parsers fail:** runtime fallback/version pin/feature-flag behavior and operator runbook notes.

Tickets missing any of the above are not implementation-ready.

## 6) PR checklist enforcement for contract-impacting changes

For Layer 5 contract-impacting PRs, authors must complete the Layer 5 compatibility section in the PR template and link this policy.

Required PR evidence:

- Compatibility classification recorded.
- Consumer impact assessment recorded.
- Rollback behavior documented.
- OpenAPI/contracts/client/test updates completed (or explicitly justified if not applicable).
