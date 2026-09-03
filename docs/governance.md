# Governance

## Overview

Every AI-generated object must be reviewable, traceable, and approvable.

## Engineering Governance Linkage

These documents define the required engineering governance path for platform changes:

- [`docs/contract.md`](contract.md): canonical platform contract and enforcement targets
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md): contributor onboarding entry point
- [`governance/launch-drift-prevention-sop.md`](governance/launch-drift-prevention-sop.md):
  required approvals for contract, tenant-isolation, and compatibility-shim changes
- [`governance/multitenancy-production-checklist.md`](governance/multitenancy-production-checklist.md):
  canonical 25-section production release gate for multitenancy and tenant isolation
- [`governance/multitenancy-baseline-assessment.md`](governance/multitenancy-baseline-assessment.md):
  baseline assessment and audit matrix against the 25-section multitenancy release gate
- [`governance/pre-stabilization-intake.md`](governance/pre-stabilization-intake.md):
  operational branch, PR, freeze, and entry gate before stabilization begins
- [`launch/stabilization-gate-0-intake-2026-06-03.md`](launch/stabilization-gate-0-intake-2026-06-03.md):
  current Gate 0 intake snapshot and blocker register for the stabilization start decision
- [`governance/pr-triage-policy.md`](governance/pr-triage-policy.md): stalled PR definitions,
  disposition labels, owner/next-action requirements, and stale-branch stabilization rules
- [`../.github/pull_request_template.md`](../.github/pull_request_template.md): PR confirmations
  required before review

Pull requests that touch backend, frontend, or API surfaces are expected to declare contract-shape,
tenant-isolation, and compatibility-shim impact explicitly and to link any required follow-up docs,
tests, or deprecation tracking.

## Review States

- `draft` - Initial generation
- `needs_review` - Flagged for human review
- `approved` - Validated by reviewer
- `modified` - Changed during review
- `rejected` - Discarded
- `published` - Approved and visible to stakeholders

## Review Queue

The Governance Review Queue surfaces:
- AI-generated hypotheses needing validation
- Formulas needing approval
- Evidence needing verification

## Production Gates

| Gate | Category | Status |
|------|----------|--------|
| Architecture | architecture | passed |
| Security | security | passed |
| Tenant Isolation | tenant_isolation | passed |
| Contract Drift | contract_drift | pending |
| Observability | observability | passed |
| Agent Safety | agent_safety | pending |

## Audit Log

Tracks:
- User actions
- Agent actions
- Review decisions
- Data changes

## Ground Truth

Validated truth objects store human-verified claims with evidence and reviewer attribution.

## Static Tenant Inference Enforcement (Runtime)

The CI static gate `scripts/ci/boundary_check.py` is blocking for runtime source trees:

- `services/**/*.py`
- `value_fabric/**/*.py`
- `packages/shared/src/shared/**/*.py`

Outside explicit allowlisted compatibility resolver code, runtime code MUST NOT infer tenant context from:

- `request.headers.get("X-Tenant-ID")`
- `request.query_params`
- `.get("tenant_id")` on request payload/query objects
- `api_key.tenant_id` or `getattr(api_key, "tenant_id", ...)`

Allowed exceptions are limited to:

- shared tenant resolver compatibility paths under `packages/shared/src/shared/identity/*` and `packages/shared/src/shared/boundaries/tenant_boundary.py`
- static checker tests and fixtures only

There are no non-production runtime exceptions for these patterns outside the allowlist.


## ADR Numbering Policy

Architecture Decision Records use a canonical filename and header format per corpus:

- Canonical architecture corpus: `docs/explanations/adr/` with filename `ADR-###-slug.md` and H1 `# ADR-###: Title`
- Implementation decisions corpus: `docs/decisions/` with filename `NNNN-slug.md` and H1 `# ADR-NNNN: Title`
- Sequence policy: IDs are contiguous within each corpus
- Machine registry: `docs/decisions/adr-registry.yaml` maps every ADR to related code paths and optional content assertions

Legacy ADR IDs are normalized during migration by reindexing to the next available sequential ID and preserving the original title/decision content.

CI enforcement: `make check-adr` (`python scripts/ci/check_adr.py`) fails if IDs are duplicated, sequence IDs are missing, filename/header IDs drift, the registry is incomplete, a related path is missing, an index table is stale, or a declared `must_contain` / `must_not_contain` rule fails.

## Kubernetes Deployment SecurityContext Standard

All rendered deployment bundles under `k8s/deployments/*` must enforce baseline Kubernetes hardening on every `Deployment`:

- Pod `securityContext.runAsNonRoot: true`
- Pod `securityContext.seccompProfile.type: RuntimeDefault`
- Container `securityContext.allowPrivilegeEscalation: false`
- Container `securityContext.readOnlyRootFilesystem: true` (unless a documented technical exception is required)
- Container `securityContext.capabilities.drop` includes `ALL`

CI enforcement: `python scripts/ci/k8s_routing_check.py` now fails when rendered deployment manifests violate this baseline, so regressions are blocked during PR validation.
