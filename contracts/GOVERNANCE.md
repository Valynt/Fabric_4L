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

## 6. Schema Registry

All JSON Schema contracts that cross service boundaries must be registered in the canonical Schema Registry (`contracts/jsonschema/registry.yaml`).

### 6.1 Lifecycle
Every schema record moves through the following lifecycle:
- **DRAFT** — under active design; may change without compatibility constraints.
- **REVIEW** — proposed for publication; subject to Council review.
- **PUBLISHED** — immutable baseline; all subsequent changes must satisfy the declared compatibility policy.
- **DEPRECATED** — still served but scheduled for removal; consumers should migrate.
- **RETIRED** — no longer served; retained only for audit and historical bundles.

Valid transitions: DRAFT ↔ REVIEW, REVIEW → PUBLISHED, PUBLISHED → DEPRECATED, DEPRECATED → RETIRED.
Forbidden transitions include any move back from PUBLISHED to DRAFT or REVIEW, and any return from RETIRED.

### 6.2 Compatibility Policy
The default policy is **ADDITIVE_WITHIN_MAJOR**. Within a major version, only additive changes are permitted:
- Adding optional fields is allowed.
- Removing fields, changing types, narrowing constraints, shrinking enums, tightening `additionalProperties`, changing `$id`, or altering semantic meaning is forbidden.

Policies also include **NONE** (no guarantees) and **FULL** (any change is breaking). The policy for each schema is declared in its registry record and enforced by CI.

### 6.3 Authoring Directions
- **SCHEMA_FIRST** — canonical artifact is the JSON Schema; all other representations are derived.
- **CODE_FIRST_WITH_GENERATED_SCHEMA** — canonical artifact is source code (e.g., Pydantic); generated schema must not be hand-edited without a matching source change.
- **OPENAPI_FIRST** / **ASYNCAPI_FIRST** — canonical artifact is the OpenAPI/AsyncAPI document; JSON Schema fragments are extracted from it.

CI gates enforce unidirectional flow: once a direction is declared, derived artifacts must not be modified independently.

### 6.4 Common Value Objects
Shared value objects (Money, Actor, Timestamp, Quantity, Identifier, EventEnvelope, ErrorEnvelope) live under `contracts/jsonschema/common/v1/` and are referenced by domain schemas via `$ref`. Changes to common schemas trigger impact analysis that lists all dependent domain schemas.

### 6.5 CI Enforcement
The following gates run on every PR that touches `contracts/jsonschema/**`:
- `check-schema-registry` — integrity, artifact existence, content-hash verification, hand-editing detection.
- `check-schema-compatibility` — diff changed schemas against their latest PUBLISHED version; fail on policy violation.
- `generate-schema-bundle` — produce a deterministic bundle with resolved `$ref` graph and a lockfile for downstream pinning.

### 6.6 Ownership
Each schema record declares an `owner` field (team/subsystem). The owner is responsible for review, deprecation planning, and migration guidance. Platform/Contracts team owns `common/*` schemas.
