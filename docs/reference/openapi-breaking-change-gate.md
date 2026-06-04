# OpenAPI Breaking-Change Gate

Fabric 4L is an OpenAPI/REST platform. Protobuf/gRPC-oriented checks such as
`buf breaking` are therefore not applicable to the repository's canonical API
contracts. The architecture-correct replacement is the OpenAPI breaking-change
gate:

```bash
pnpm contract:breaking
```

The gate compares the current branch's `contracts/openapi/*.json` artifacts to
the baseline branch (default: `origin/main`) and emits both:

- `artifacts/contract-breaking/openapi-breaking-report.json`
- `artifacts/contract-breaking/openapi-breaking-report.md`

Generated reports are runtime artifacts and are not committed by default.

## Breaking changes detected

The check fails for unapproved changes in these categories:

- Removed paths.
- Removed methods.
- Removed request fields.
- Removed response fields.
- Type narrowing or incompatible type changes.
- Enum value removals.
- Auth/security contract changes.
- Required field additions.
- Error response contract drift, including removed error statuses, removed error
  media types, and field/type drift inside `4xx` or `5xx` response schemas.

## Approval model

Breaking changes are blocked unless they have an approved RFC/deprecation record
in `docs/governance/openapi-breaking-change-exceptions.json`. Each exception
must be temporary, have `status: "approved"`, include an `approvedBy` value, and
reference either a Contract Change RFC or a deprecation record.

Use the fingerprints from the generated JSON or Markdown report for the most
precise approval. Path/category matches are supported for coordinated endpoint
migrations, but fingerprints are preferred because they bind the exception to a
specific contract location.

Example exception:

```json
{
  "id": "OAPI-BREAK-2026-001",
  "status": "approved",
  "approvedBy": "contract-council",
  "rfc": "https://github.com/valuefabric/fabric-4l/issues/1234",
  "deprecationRecord": "DEP-API-V1-SUNSET-001",
  "expiresOn": "2026-07-31T00:00:00Z",
  "fingerprints": ["0123456789abcdef"],
  "matches": []
}
```

## CI wiring

`contract-compliance.yml` runs `pnpm contract:breaking` after the contract
freshness/type-generation gate. On pull requests it uses the PR base branch as
the baseline ref; on scheduled or branch runs it defaults to `origin/main`.
The workflow uploads the JSON and Markdown reports on every run.

This explicitly replaces any non-applicable `buf breaking` requirement for
Fabric 4L OpenAPI/REST contracts.
