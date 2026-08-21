## Summary

- Describe what changed and why.

## Governance Impact (Required for backend/frontend/API changes)

- **Contract shape impact:** None | Additive | Breaking | Docs/tests only
- **Tenant isolation impact:** None | Reviewed-no-impact | Behavior changed and covered
- **Compatibility shim impact:** None | Added | Modified | Removed
- [ ] I updated contract definitions/types/tests/docs for any contract-shape change.
- [ ] I verified tenant scoping and authenticated context handling for affected backend data paths.
- [ ] I updated shim tracking or deprecation evidence for any compatibility-shim change.

## Change Type

- [ ] Feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Refactor/maintenance


## API Evolution (Required for Phase 3 Feature Tickets)

- **Route(s) affected:**
- **Additive field list:**
- **Backward compatibility guarantee:**
- **Versioning decision:**
- **Deprecation plan (if applicable):**

### Layer 5 Compatibility Policy (Required for contract-impacting Layer 5 changes)

Reference: `docs/reference/layer5-api-compatibility-policy.md`

- **Compatibility classification:** Additive-safe | Breaking
- **Consumer impact assessment:** (frontend, generated clients, Layer 4, Layer 6, external consumers)
- **Rollback behavior if downstream parsers fail:**
- [ ] Completed required frontend/generated-client update steps per policy.
- [ ] Completed required Layer 4 / Layer 6 integration test updates per policy.

### Phase 3 API Evolution Linked Updates (Required When L5 API Surface Changes)

- [ ] Updated `contracts/openapi/layer5-ground-truth.json`.
- [ ] Regenerated and committed generated client outputs for impacted surfaces.
- [ ] Updated consumer integration tests for impacted Layer 4 / Layer 6 paths.

## Release & Policy Checklist (Required)

- [ ] If API behavior/contracts changed, I updated `contracts/openapi/` and/or `contracts/jsonschema/`.
- [ ] If API changes are breaking, I created/updated a major version and included migration guidance.
- [ ] If deprecating APIs, I documented deprecation start and sunset dates per `docs/api-versioning-policy.md`.
- [ ] I reviewed DR expectations in `docs/reliability/dr-policy.md` and updated recovery docs if service criticality changed.
- [ ] For resilience-impacting changes, I updated or validated DR runbooks in `docs/runbooks/`.
- [ ] If this PR claims Layer 5 Phase 0 closure/readiness, all discovered Layer 5 issues include owner and due date (per `docs/governance/layer5-backlog-issue-template.md`); otherwise Phase 0 remains open.
- [ ] I validated release readiness with either successful chaos smoke + blue-green health-gate checks, or attached an approved exception.


## Incremental PR Gate Reporting (Required)

For every incremental PR, provide explicit **Pass / Fail** status and evidence links (job URL, run ID, or log artifact) for each gate below.

| Gate | Status (Pass/Fail) | Evidence (URL or artifact) | Notes |
|---|---|---|---|
| structural-preflight |  |  |  |
| Service layer lint/type/test jobs |  |  |  |
| Layer 5 source/tenant/contract gates |  |  |  |
| contract-checks |  |  |  |
| runtime-contract-checks |  |  |  |
| route-auth-gate |  |  |  |
| production-readiness-gate |  |  |  |
| unified-readiness-gate |  |  |  |

### Behavior Parity (Required for incremental PRs)

- [ ] Behavior parity verified against baseline snapshots captured in Step 1 (attach snapshot references/diffs).

## Why overlap is expected

- Required when PR overlap guard reports high overlap with recently merged PRs.
- Explain why overlap is intentional, what was reused/coordinated, and why risk is acceptable.

## Validation

- [ ] `make verify`
- [ ] `make production-readiness-gate`
- [ ] `make evals` (required for agent/skill prompt changes)

## Code Quality Checklist

- [ ] Accessibility checks passed (`pnpm run test:a11y:components`, `pnpm run test:a11y:pages`, `pnpm run test:a11y:gate`).
- [ ] Keyboard navigation acceptance criteria validated for changed UX flows.
- [ ] Screen-reader announcements/labels validated for changed UX flows.
- [ ] If requesting a temporary accessibility exception, linked remediation ticket + due date.
- [ ] No unused imports (ruff F401)
- [ ] No unused variables (ruff F841)
- [ ] No `console.log` in production code (without DEV guard)
- [ ] All TODOs reference a ticket (TODO: TICKET-123 format)
- [ ] No dead code blocks (commented-out code > 3 lines)

## Risks / Rollback

- Known risks:
- Rollback plan:

## PR Size & Status Policy

- [ ] This PR is small and focused on a single logical change.
- [ ] If this PR is still a Work-In-Progress, I have marked it as a **Draft** PR.
- [ ] (For maintainers) If this PR is a trivial change (docs, dependabot group, minor fix), it can be fast-tracked for merge.
- **Size justification:** <!-- Required when the PR is large (>1000 net additions, excluding generated/lockfile paths). Replace this comment with a concrete rationale for why this change could not be split into smaller PRs. Leave blank for small/medium PRs. -->
