# Contract Council Governance & RFC Process

## 1. Overview
The **Contract Council** is the governing body responsible for maintaining the integrity, security, and backward compatibility of all API contracts (OpenAPI and JSON Schema) within the Fabric 4L Data Integration Layer (DIL).

Because the DIL serves as the central nervous system connecting the frontend, backend microservices, and agentic workflows, any change to its contracts can have cascading effects. The RFC (Request for Comments) process ensures that all contract changes are deliberately designed, reviewed, and communicated before implementation.

## 2. The Contract Council
The Contract Council consists of representatives from:
- **Frontend Engineering:** Ensures UI requirements are met and hook generation remains stable.
- **Backend Engineering:** Ensures performance, scalability, and implementation feasibility.
- **Platform/Security:** Ensures tenant isolation, RBAC enforcement, and compliance.

### Responsibilities
- Review and approve all Contract RFCs.
- Enforce the API Boundary Contract (`contracts/frontend/01-api-boundary-contract.md`).
- Maintain the canonical OpenAPI specs and JSON Schemas.
- Coordinate breaking changes and migration strategies.

## 3. The RFC Process
Any engineer proposing a change to an existing contract or introducing a new contract must follow this process:

### Step 1: Draft the RFC
Create a new GitHub Issue using the **Contract Change RFC** template. The RFC must clearly articulate the motivation, the exact schema changes, and a breaking change assessment.

### Step 2: Council Review
The RFC is labeled `needs-council-review`. Council members will review the proposal asynchronously. The review focuses on:
- **Consistency:** Does it follow existing naming conventions and error shapes?
- **Security:** Does it expose sensitive data or bypass tenant scoping?
- **Compatibility:** Is it a breaking change? If so, is the migration plan sound?

### Step 3: Approval & Implementation
Once the RFC receives approval from at least two Council members (representing different domains), it is marked `approved`. The engineer may then proceed with the implementation PR.

### Step 4: CI Enforcement
The CI pipeline includes a `contract-rfc-enforcer` check defined in `.github/workflows/contract-rfc-enforcer.yml`. It triggers on any PR that modifies files under `contracts/openapi/` or `contracts/jsonschema/`. The check fails unless the PR description references an approved RFC issue (e.g., `Closes #123`). The enforcer script is at `.github/scripts/contract-rfc-enforcer.sh`.

## 4. Breaking Changes Policy
A breaking change is defined as any modification that would cause an existing, compliant client to fail. Examples include:
- Removing a field from a response payload.
- Changing the data type of a field.
- Adding a new required field to a request payload.
- Changing authentication requirements.

**Policy:** Breaking changes are strongly discouraged. When unavoidable, they require a coordinated release plan, including a deprecation period for the old contract and versioning of the endpoint (e.g., `/api/v2/...`).

## 5. Emergency Hotfixes
In the event of a critical security vulnerability or a Sev-1 production incident, the RFC process may be bypassed to expedite a fix. The engineer must still document the contract change retroactively by filing an RFC within 24 hours of the hotfix deployment.

## 6. OpenAPI Breaking-Change Gate

This repository uses OpenAPI/REST contracts rather than Protobuf/gRPC, so `buf breaking` is intentionally **not applicable**. The replacement governance gate is the repository-owned OpenAPI breaking-change check:

```bash
pnpm contract:breaking
```

The command compares `contracts/openapi/*.json` on the current branch against the baseline branch (`OPENAPI_BREAKING_BASE_REF`, `GITHUB_BASE_REF`, `origin/main`, `main`, or `HEAD~1`, in that order) and fails on unapproved breaking changes. It detects:

- Removed paths and methods.
- Removed request and response fields.
- Type narrowing, including stricter scalar constraints.
- Enum value removals.
- Auth/security requirement changes.
- Required field additions.
- Error response contract drift for 4xx/5xx responses.

Every run emits both report artifacts:

- `reports/contracts/openapi-breaking-report.json`
- `reports/contracts/openapi-breaking-report.md`

Breaking findings are allowed to pass only when they match an approved deprecation record in `contracts/deprecations/generated-contract-deprecations.json` or an approved Contract Council RFC in `contracts/rfcs/`. Otherwise CI fails in `.github/workflows/contract-compliance.yml`.
