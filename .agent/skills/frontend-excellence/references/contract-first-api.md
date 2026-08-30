# Contract-First API Design

**Destination:** Frontend and backend stay in lockstep because the API shape is defined as typed schemas *before* any implementation, and drift is caught by CI.

## Steps

1. **Locate the contract sources of truth** — `contracts/openapi/` and `contracts/jsonschema/`. These are canonical; routes and clients must match them.
2. **Define the schema before code.** For a new endpoint:
   - Path, method, request/response DTOs, error shapes, auth requirements.
   - Tenant scoping: data is owned by `tenant_id` from authenticated context — never trust a body-supplied tenant ID.
   - Error model: stable codes, no stack traces, no secrets in messages.
3. **Generate types/code from the spec.** Regenerate the API client and TS types from OpenAPI; do not hand-maintain DTO types.
4. **Align every consumer.** If the response shape changes, update: OpenAPI spec → JSON Schema → generated TS types → TanStack Query hooks → UI consumers → tests → docs. Never silently change a response shape.
5. **Route-grade validation.** In the frontend, validate response payloads with Zod at the network boundary (or domain parsers) before UI components consume them.
6. **Reference existing agreement.** When relevant, run the repo's contract compliance: `pnpm run check:contract-compliance`, `pnpm run check:api-types`, `make contract-tests`.

## Common Failure

**Frontend calls drift from backend prefixes.** A `/v1/layerX` prefix mismatch between the frontend API client and the FastAPI router causes 404s in production even when everything works locally. Always diff frontend call paths against the OpenAPI spec.

## Verification

```bash
# Enforce spec == implementation
pnpm run check:contract-compliance
pnpm run check:api-types
make contract-tests          # backend contract tests
```