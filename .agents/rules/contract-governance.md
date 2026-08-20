# Contract Governance Rule

Contracts in `contracts/` and OpenAPI specifications are the single source of truth.

## Principles
1. **Source of Truth**: `contracts/openapi/` and `contracts/jsonschema/` define platform interfaces.
2. **No Silent Drift**: Never alter route response shapes, field names, or types without updating the OpenAPI spec, TypeScript types, and contract tests.
3. **Drift Verification**: Before committing changes touching APIs, run `pnpm run check:contract-compliance` and `pnpm run check:api-types`.
4. **Failure Modes**: Contract definitions must specify structured error responses (e.g. standard RFC 7807 problem details or typed error DTOs), not generic string errors.
