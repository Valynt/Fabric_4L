# Fabric_4L API Reference

This directory documents the production Fabric_4L unified API described by `contracts/openapi/fabric-4l-api.json`. The contract is intended for client integrations, security assessments, and automated conformance checks.

## Contract status

- **OpenAPI version:** 3.1.0
- **API version:** 1.0.0
- **Authentication scheme:** `Authorization: Bearer <JWT>` for tenant-scoped `/v1/*` endpoints.
- **Unauthenticated operational endpoints:** `/ready`, `/health`, and `/metrics` expose platform health or metrics surfaces and should be protected by deployment/network policy.
- **Internal webhook endpoint:** `/internal/webhooks/clerk` is mounted for identity-provider webhook delivery; production deployments must restrict it with webhook signature validation and network policy.

## Endpoint inventory

| Method | Path | Tags | Auth | Rate limit | Purpose |
|---|---|---|---|---|---|
| `GET` | `/health` | Platform, health | Public operational endpoint | Exempt operational/internal tier (network controls still apply) | Default Handler |
| `POST` | `/internal/webhooks/clerk` | Platform, internal-webhooks | No bearer; internal webhook signature/network controls | Exempt operational/internal tier (network controls still apply) | Clerk Webhook |
| `GET` | `/metrics` | Platform | Public operational endpoint | Exempt operational/internal tier (network controls still apply) | Metrics |
| `GET` | `/ready` | Platform, health | Public operational endpoint | Exempt operational/internal tier (network controls still apply) | Readiness Handler |
| `GET` | `/v1/accounts` | L4-Agents, Accounts | Bearer JWT required | Default tenant tier | List Accounts |
| `POST` | `/v1/accounts` | L4-Agents, Accounts | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Account |
| `GET` | `/v1/accounts/{account_id}` | L4-Agents, Accounts | Bearer JWT required | Default tenant tier | Get Account |
| `PATCH` | `/v1/accounts/{account_id}` | L4-Agents, Accounts | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Update Account |
| `GET` | `/v1/accounts/{account_id}/drivers` | L4-Agents, Driver Tree | Bearer JWT required | Default tenant tier | List Drivers |
| `POST` | `/v1/accounts/{account_id}/drivers/generate` | L4-Agents, Driver Tree | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Generate Driver |
| `PATCH` | `/v1/accounts/{account_id}/drivers/{driver_id}` | L4-Agents, Driver Tree | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Update Driver |
| `GET` | `/v1/accounts/{account_id}/enrichment` | L1-Ingestion, Intelligence | Bearer JWT required | Default tenant tier | Get Enrichment |
| `GET` | `/v1/accounts/{account_id}/evidence` | L5-Ground-Truth, Evidence | Bearer JWT required | Default tenant tier | List Evidence |
| `POST` | `/v1/accounts/{account_id}/evidence/match` | L5-Ground-Truth, Evidence | Bearer JWT required | Extraction tier: 60/min, 2,000/hour, burst 15 | Match Evidence |
| `GET` | `/v1/accounts/{account_id}/evidence/{evidence_id}` | L5-Ground-Truth, Evidence | Bearer JWT required | Default tenant tier | Get Evidence |
| `POST` | `/v1/accounts/{account_id}/evidence/{evidence_id}/pii-scan` | L5-Ground-Truth, Evidence | Bearer JWT required | Extraction tier: 60/min, 2,000/hour, burst 15 | Scan Evidence Pii |
| `GET` | `/v1/accounts/{account_id}/gates` | L4-Agents, Value Case | Bearer JWT required | Default tenant tier | Get Account Gates |
| `GET` | `/v1/accounts/{account_id}/hypotheses` | L4-Agents, Hypotheses | Bearer JWT required | Default tenant tier | List Hypotheses |
| `POST` | `/v1/accounts/{account_id}/hypotheses/generate` | L4-Agents, Hypotheses | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Generate Hypothesis |
| `PATCH` | `/v1/accounts/{account_id}/hypotheses/{hypothesis_id}` | L4-Agents, Hypotheses | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Update Hypothesis |
| `GET` | `/v1/accounts/{account_id}/ontology-match` | L2-Extraction, Intelligence | Bearer JWT required | Default tenant tier | Get Ontology Match |
| `GET` | `/v1/accounts/{account_id}/realization-plans` | L4-Agents, Realization | Bearer JWT required | Default tenant tier | List Realization Plans |
| `POST` | `/v1/accounts/{account_id}/realization-plans` | L4-Agents, Realization | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Realization Plan |
| `PATCH` | `/v1/accounts/{account_id}/realization-plans/{plan_id}/actuals` | L4-Agents, Realization | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Update Actuals |
| `GET` | `/v1/accounts/{account_id}/realization-plans/{plan_id}/recommendations` | L4-Agents, Realization | Bearer JWT required | Default tenant tier | Get Recommendations |
| `GET` | `/v1/accounts/{account_id}/realization-plans/{plan_id}/variance` | L4-Agents, Realization | Bearer JWT required | Default tenant tier | Get Variance |
| `GET` | `/v1/accounts/{account_id}/reviews` | L4-Agents, Reviews | Bearer JWT required | Default tenant tier | List Review Requests |
| `POST` | `/v1/accounts/{account_id}/reviews` | L4-Agents, Reviews | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Review Request |
| `GET` | `/v1/accounts/{account_id}/reviews/{review_id}` | L4-Agents, Reviews | Bearer JWT required | Default tenant tier | Get Review Request |
| `PATCH` | `/v1/accounts/{account_id}/reviews/{review_id}` | L4-Agents, Reviews | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Update Review Request |
| `GET` | `/v1/accounts/{account_id}/reviews/{review_id}/comments` | L4-Agents, Reviews | Bearer JWT required | Default tenant tier | List Review Comments |
| `POST` | `/v1/accounts/{account_id}/reviews/{review_id}/comments` | L4-Agents, Reviews | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Review Comment |
| `GET` | `/v1/accounts/{account_id}/roi-calculations/{calculation_id}` | L4-Agents, Calculator | Bearer JWT required | Default tenant tier | Get Roi Calculation |
| `POST` | `/v1/accounts/{account_id}/roi/calculate` | L4-Agents, Calculator | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Run Roi Calculation |
| `GET` | `/v1/accounts/{account_id}/scenarios` | L4-Agents, Calculator | Bearer JWT required | Default tenant tier | List Scenarios |
| `POST` | `/v1/accounts/{account_id}/scenarios` | L4-Agents, Calculator | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Scenario |
| `DELETE` | `/v1/accounts/{account_id}/share` | L4-Agents, Accounts | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Revoke Share Link |
| `POST` | `/v1/accounts/{account_id}/share` | L4-Agents, Accounts | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Share Link |
| `GET` | `/v1/accounts/{account_id}/signals` | L1-Ingestion, Intelligence | Bearer JWT required | Default tenant tier | List Signals |
| `POST` | `/v1/accounts/{account_id}/signals/extract` | L1-Ingestion, Intelligence | Bearer JWT required | Extraction tier: 60/min, 2,000/hour, burst 15 | Extract Signal |
| `GET` | `/v1/accounts/{account_id}/snapshots` | L4-Agents, Versioning | Bearer JWT required | Default tenant tier | List Snapshots |
| `POST` | `/v1/accounts/{account_id}/snapshots` | L4-Agents, Versioning | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Snapshot |
| `GET` | `/v1/accounts/{account_id}/snapshots/{snapshot_id}` | L4-Agents, Versioning | Bearer JWT required | Default tenant tier | Get Snapshot |
| `POST` | `/v1/accounts/{account_id}/snapshots/{snapshot_id}/diff` | L4-Agents, Versioning | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Diff Snapshots |
| `POST` | `/v1/accounts/{account_id}/snapshots/{snapshot_id}/restore` | L4-Agents, Versioning | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Restore Snapshot |
| `GET` | `/v1/accounts/{account_id}/stakeholders` | L1-Ingestion, Intelligence | Bearer JWT required | Default tenant tier | List Stakeholders |
| `GET` | `/v1/accounts/{account_id}/summary` | L4-Agents, Accounts | Bearer JWT required | Default tenant tier | Get Account Summary |
| `GET` | `/v1/accounts/{account_id}/value-case` | L4-Agents, Value Case | Bearer JWT required | Default tenant tier | Get Value Case |
| `POST` | `/v1/accounts/{account_id}/value-case/generate` | L4-Agents, Value Case | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Generate Value Case |
| `POST` | `/v1/accounts/{account_id}/value-case/{value_case_id}/export` | L4-Agents, Value Case | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Export Value Case |
| `PATCH` | `/v1/accounts/{account_id}/value-cases/{value_case_id}` | L4-Agents, Value Case | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Update Value Case |
| `GET` | `/v1/accounts/{account_id}/value-tree` | L4-Agents, Driver Tree | Bearer JWT required | Default tenant tier | Get Value Tree |
| `POST` | `/v1/agents/runs` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Create Agent Run |
| `GET` | `/v1/agents/runs/{run_id}` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Get Agent Run |
| `POST` | `/v1/agents/runs/{run_id}/cancel` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Cancel Agent Run |
| `POST` | `/v1/agents/runs/{run_id}/resume` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Resume Agent Run |
| `POST` | `/v1/agents/workflows` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Create Workflow |
| `GET` | `/v1/agents/workflows/active` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | List Active Workflows |
| `DELETE` | `/v1/agents/workflows/{id}` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Cancel Workflow |
| `GET` | `/v1/agents/workflows/{id}` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Get Workflow |
| `GET` | `/v1/agents/workflows/{id}/events` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Workflow Events |
| `POST` | `/v1/agents/workflows/{id}/pause` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Pause Workflow |
| `POST` | `/v1/agents/workflows/{id}/resume` | L4-Agents, Agents | Bearer JWT required | Agent execution tier: 40/min, 1,200/hour, burst 10 | Resume Workflow |
| `GET` | `/v1/context-engine/benchmarks` | L6-Benchmarks, Context Engine | Bearer JWT required | Default tenant tier | List Benchmarks |
| `GET` | `/v1/context-engine/formulas` | L6-Benchmarks, Context Engine | Bearer JWT required | Default tenant tier | List Formulas |
| `GET` | `/v1/context-engine/formulas/{formula_id}` | L6-Benchmarks, Context Engine | Bearer JWT required | Default tenant tier | Get Formula |
| `GET` | `/v1/context-engine/ontology` | L6-Benchmarks, Context Engine | Bearer JWT required | Default tenant tier | Get Ontology |
| `GET` | `/v1/context-engine/value-packs` | L6-Benchmarks, Context Engine | Bearer JWT required | Default tenant tier | List Value Packs |
| `GET` | `/v1/context-engine/value-packs/{value_pack_id}` | L6-Benchmarks, Context Engine | Bearer JWT required | Default tenant tier | Get Value Pack |
| `GET` | `/v1/governance/audit-log` | L5-Ground-Truth, Governance | Bearer JWT required | Default tenant tier | Get Audit Log |
| `GET` | `/v1/governance/prod-gates` | L5-Ground-Truth, Governance | Bearer JWT required | Default tenant tier | List Prod Gates |
| `POST` | `/v1/governance/review-decisions` | L5-Ground-Truth, Governance | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Review Decision |
| `GET` | `/v1/governance/review-queue` | L5-Ground-Truth, Governance | Bearer JWT required | Default tenant tier | Get Review Queue |
| `GET` | `/v1/intelligence/account/{account_id}/enrichment` | L1-Ingestion, Intelligence | Bearer JWT required | Default tenant tier | Get Enrichment Legacy |
| `GET` | `/v1/intelligence/account/{account_id}/ontology-match` | L2-Extraction, Intelligence | Bearer JWT required | Default tenant tier | Get Ontology Match Legacy |
| `GET` | `/v1/intelligence/account/{account_id}/signals` | L1-Ingestion, Intelligence | Bearer JWT required | Default tenant tier | List Signals Legacy |
| `POST` | `/v1/intelligence/account/{account_id}/signals/extract` | L1-Ingestion, Intelligence | Bearer JWT required | Extraction tier: 60/min, 2,000/hour, burst 15 | Extract Signal Legacy |
| `GET` | `/v1/intelligence/account/{account_id}/stakeholders` | L1-Ingestion, Intelligence | Bearer JWT required | Default tenant tier | List Stakeholders Legacy |
| `POST` | `/v1/privacy/dsar` | L5-Ground-Truth, Privacy | Bearer JWT required | Default tenant tier; idempotency enforced for writes | Create Dsar |
| `GET` | `/v1/privacy/dsar/packages/{package_id}/download` | L5-Ground-Truth, Privacy | Bearer JWT required | Default tenant tier | Download Dsar Package |
| `GET` | `/v1/privacy/dsar/{request_id}` | L5-Ground-Truth, Privacy | Bearer JWT required | Default tenant tier | Get Dsar |

## Authentication guide

Fabric_4L uses bearer JWT authentication for all tenant-scoped API operations.

1. **Sign in through the configured identity provider.** Production environments use Clerk as the primary IdP (`VITE_AUTH_PROVIDER=clerk`) and request a token from the configured Clerk JWT template (`VITE_CLERK_JWT_TEMPLATE=fabric4l-api`). Keycloak/OIDC variables remain available for deployments that use an OIDC-compatible provider.
2. **Request an API token.** Browser clients obtain a JWT from the configured frontend auth SDK. Server-side clients should use the organization-approved OAuth/OIDC or Clerk machine-to-machine flow for the same audience configured by `CLERK_JWT_AUDIENCE` or `JWT_AUDIENCE`.
3. **Send the token on every tenant-scoped request.**

```http
Authorization: Bearer <access_token>
```

4. **Refresh before expiry.** Use the refresh-token flow supplied by the configured identity provider. The Fabric_4L API validates access tokens; it does not expose a public refresh endpoint in this OpenAPI contract. Clients should refresh through Clerk/OIDC and retry the original request once after receiving a token-expiry `401`.
5. **Do not rely on request-body tenant IDs.** Tenant ownership is derived from authenticated context; request payload tenant fields are informational or validated against that context.

## Error code reference

| Status | Error class | Integration guidance |
|---|---|---|
| `400` | Bad request | Correct malformed JSON, invalid query parameters, or unsupported workflow inputs. |
| `401` | Unauthorized | Acquire or refresh the bearer JWT and retry once. |
| `403` | Forbidden | The principal is authenticated but lacks role, tenant, or resource authorization. Do not retry without permission changes. |
| `404` | Not found | The resource does not exist or is not visible in the authenticated tenant scope. |
| `409` | Conflict | Resolve stale state, duplicate operation, or resource-version conflict before retrying. |
| `422` | Validation error | Request shape failed schema validation; inspect `detail` fields and fix the payload. |
| `429` | Rate limited | Back off until `Retry-After`; inspect `X-RateLimit-*` headers for remaining quota and reset time. |
| `500` | Internal server error | Treat as transient only after confirming idempotency; include request ID when escalating. |
| `503` | Service unavailable | Dependency or readiness failure; retry with exponential backoff. |

Error responses use structured JSON bodies where available. Rate-limit failures include `detail`, `error`, and `retry_after` fields plus rate-limit headers.

## Rate limiting policy

Fabric_4L enforces tenant-scoped sliding-window limits. The effective key includes tenant, caller, and route classification when the corresponding `RATE_LIMIT_KEY_INCLUDE_*` environment flags are enabled.

| Tier | Applies to | Limit |
|---|---|---|
| Shared tenant | Default tenant tier | 100 requests/minute, 5,000/hour, 100,000/day, burst 20 |
| Dedicated tenant | Higher-capacity tenant tier | 500 requests/minute, 25,000/hour, 500,000/day, burst 100 |
| Enterprise tenant | Enterprise tenant tier | 2,000 requests/minute, 100,000/hour, 2,000,000/day, burst 500 |
| Agent execution route group | Agent runs, workflow control, generation-heavy orchestration | 40 requests/minute, 1,200/hour, burst 10 |
| Extraction route group | Signal extraction, evidence matching, PII scans | 60 requests/minute, 2,000/hour, burst 15 |
| Model registry write route group | High-cost model registry writes if mounted | 20 requests/minute, 600/hour, burst 5 |
| Exempt operational/internal prefixes | `/health`, `/metrics`, configured internal health/metrics prefixes | Exempt from tenant rate limiting; protect with network and observability policy |

All write methods (`POST`, `PUT`, `PATCH`, `DELETE`) are also covered by the API gateway idempotency policy where enabled.

## Contract-quality expectations

- Every operation must include a meaningful description.
- Every operation must include an explicit Fabric layer tag (`L1-Ingestion` through `L6-Benchmarks`, or `Platform` for operational/internal surfaces).
- Every parameter and schema/property must be described.
- Every documented write request body must include examples, and successful write responses with JSON content must include examples.
- CI runs `scripts/ci/validate_fabric_openapi_docs.py` on PRs to enforce these rules.
