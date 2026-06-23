# Contract Versioning and Deprecation Policy

## Versioning

- API contracts follow path-based versioning (`/api/v1/...`, `/api/v2/...`).
- Event contracts include a `contract_version` field in the envelope.
- Data contracts follow the migration revision ID.
- AI/tool contracts follow the manifest filename version suffix.

## Breaking changes

A breaking change is any modification that causes an existing compliant consumer to fail. Examples:

- Removing a response field
- Adding a required request field
- Changing a field type or semantic meaning
- Changing authentication requirements

## RFC process

All breaking changes require a Contract Council RFC (see `contracts/GOVERNANCE.md`). The RFC must include:

- Consumer impact analysis
- Migration plan
- Deprecation period
- Rollback strategy

## Compatibility window

- Standard deprecation window: 90 days.
- Security-critical changes: may be expedited with CISO approval.
- Deprecated versions are blocked from production traffic after the sunset date.

## Generated clients

`pnpm check:api-types` regenerates frontend clients and fails if they drift from the canonical OpenAPI specs.

## Enforcement

- CI: `contract-compliance.yml` runs `pnpm contract:breaking` and `python scripts/ci/contract_compliance_gate.py`.
- Runtime: API gateway rejects unknown versions and malformed messages.
- Audit: every contract change is logged with RFC reference and breaking-change assessment.

## Sunset

Once a contract version is sunset, producers and consumers must remove it. The `contract-compliance.yml` schedule checks for stale supported versions.
