# Contract Exception Policy

**Status:** Active  
**Effective Date:** 2026-04-28  
**Applies To:** All Fabric 4L canonical contracts per CONTRACT.md

---

## Purpose

This policy defines when and how exceptions to the Fabric 4L canonical contracts may be granted. The goal is to balance:

- **Enforcement:** Contracts must be followed to maintain platform integrity
- **Pragmatism**: Legitimate technical constraints may require temporary exceptions
- **Transparency**: All exceptions are tracked and subject to expiration

## Contract-Breaking API Changes

The committed OpenAPI document is the source of truth for public Layer 4
contracts. Any removal, incompatible type/required-field change, or semantic
change to an existing operation must be submitted through the repository's
OpenAPI breaking-change gate (`pnpm contract:breaking`) before merge. The gate
must run against the regenerated contract and its generated types; a green
result is required even when the implementation tests pass.

Breaking changes are not approved by changing the contract artifact directly.
If compatibility is required, ship an additive versioned route or an additive
field with an explicit migration/deprecation window. A temporary exception
uses the process below: record the exception in `deprecations.json`, link the
tracking ticket, document mitigation and expiry, and obtain the approvers
defined by the exception type. Exceptions never permit weakened authentication,
tenant isolation, or validation. The contract gate, CI reviewer, and
Architecture Review Board remain the approval model for contract changes.

---

## Exception Types

### 1. Temporary Exception (TE)

For time-bound situations where migration to the canonical pattern is in progress.

| Field | Requirement |
|-------|-------------|
| **Max Duration** | 30 days |
| **Justification** | Migration in progress with documented plan |
| **Approval** | Tech Lead + Architecture Review |
| **Extension** | One 15-day extension max |

### 2. Architectural Exception (AE)

For cases where the canonical pattern genuinely doesn't fit the use case.

| Field | Requirement |
|-------|-------------|
| **Max Duration** | 90 days (requires quarterly review) |
| **Justification** | Technical incompatibility documented in ADR |
| **Approval** | Architecture Review Board |
| **Extension** | Requires new ARB review |

### 3. Emergency Exception (EE)

For production incidents requiring immediate mitigation.

| Field | Requirement |
|-------|-------------|
| **Max Duration** | 7 days |
| **Justification** | Incident ticket with severity P0/P1 |
| **Approval** | On-call Engineer + post-hoc ARB review |
| **Extension** | Convert to TE within 48 hours |

---

## Exception Process

### Step 1: Document in Deprecation Register

Add entry to `docs/governance/deprecations.json`:

```json
{
  "id": "DEP-XXX-NNN",
  "pattern": "...",
  "status": "exception",
  "exceptionType": "TE|AE|EE",
  "exception": {
    "ticket": "JIRA-1234",
    "approvedBy": "name@example.com",
    "approvedDate": "2026-04-28",
    "expirationDate": "2026-05-28",
    "justification": "Detailed explanation",
    "mitigation": "How risk is controlled during exception period"
  }
}
```

### Step 2: Add Code Annotation

Mark exception sites in code:

```python
# CONTRACT_EXCEPTION: DEP-XXX-NNN
# Expires: 2026-05-28
# Reason: Migration to canonical pattern in progress
# ApprovedBy: name@example.com
# RiskMitigation: Isolated test environment, no production data
def legacy_function(tenant_id: str):  # noqa: DEP-XXX-NNN
    ...
```

### Step 3: CI Validation

CI will:
1. Verify exception ID exists in register
2. Verify expiration date hasn't passed
3. Verify approval chain is complete
4. Fail build if exception expired

### Step 4: Release-Scoped Auth/Tenant Placeholder Exception Tag

For release-scoped `TODO`/`FIXME` markers that mention auth, authentication, authorization, tenant, RBAC, ACL, or OIDC, CI requires structured metadata in the exception text:

```text
[auth-tenant-exception ticket=SEC-123 owner=platform.security expiry=YYYY-MM-DD]
```

Requirements:

- `ticket`: tracking ticket ID (for example `SEC-123` or `PLATSEC-4567`)
- `owner`: responsible team slug (for example `platform.security`)
- `expiry`: ISO date in `YYYY-MM-DD` format and must be current/future

Review process:

1. Author includes the structured tag in the allowlist exception metadata.
2. Reviewer verifies ticket is active and mitigation is documented.
3. Reviewer verifies owner is accountable for remediation.
4. Reviewer verifies expiry is short-lived and aligned to release risk.
5. CI blocks merge if metadata is missing, malformed, or expired.

---

## Approval Hierarchy

| Exception Type | Required Approvers | Escalation Path |
|----------------|-------------------|-----------------|
| Temporary (TE) | Tech Lead + 1 Senior Engineer | Architecture Review Board |
| Architectural (AE) | Architecture Review Board (3+ members) | CTO Decision |
| Emergency (EE) | On-call Engineer + Incident Commander | Post-incident ARB review |

---

## What Is Never Exemptible

The following are **never** eligible for exceptions:

### Security Critical
- ✓ Cross-tenant data access risks
- ✓ Raw secrets/credentials in code
- ✓ Unvalidated user input reaching DB queries
- ✓ Authentication bypass patterns

### Contract Critical
- ✓ Tenant context propagation in request handlers
- ✓ Tool boundary violations in agent execution
- ✓ Agent output validation before UI/business logic
- ✓ Inline DB sessions in request handlers

### Compliance Critical
- ✓ Audit logging requirements
- ✓ Data retention policy violations
- ✓ GDPR/privacy data handling
- ✓ Security scan soft-failing in CI

---

## Exception Register

All exceptions are tracked in `docs/governance/deprecations.json` under the `exceptions` array.

### Required Fields

| Field | Description |
|-------|-------------|
| `id` | Unique exception ID (DEP-XXX-NNN) |
| `contract` | Which canonical contract (e.g., "2.1-tenant-context") |
| `exceptionType` | TE, AE, or EE |
| `approvedBy` | Email of approver |
| `approvedDate` | ISO 8601 date |
| `expirationDate` | Hard expiration date |
| `justification` | Detailed technical rationale |
| `mitigation` | Risk controls during exception |
| `ticket` | Link to JIRA/GitHub issue |

---

## Compliance Monitoring

### Automated Checks

1. **Daily:** Expiration check in CI (contract-compliance.yml)
2. **Weekly:** Exception report to #architecture-alerts
3. **Monthly:** ARB review of all active exceptions
4. **Quarterly:** Policy effectiveness review

### Metrics

| Metric | Target |
|--------|--------|
| Active exceptions | < 10 per contract |
| Exception expiration compliance | 100% |
| Average exception duration | < 21 days |
| Emergency exceptions per quarter | < 2 |

---

## Enforcement

### CI Behavior

- **Active exception**: Build passes with warning annotation
- **Expired exception**: Build fails with error
- **Missing exception**: Build fails with error
- **Invalid exception**: Build fails with error

### Runtime Behavior

- Exceptions are logged at WARN level with full context
- Exception usage tracked in metrics
- Alert on expired exception runtime usage

---

## Policy Maintenance

### Review Schedule

| Review Type | Frequency | Owner |
|-------------|-----------|-------|
| Exception audit | Weekly | Platform Engineering |
| Policy effectiveness | Monthly | Architecture Review Board |
| Full policy review | Quarterly | CTO Office |
| Emergency policy activation | As needed | On-call + Incident Commander |

### Change Process

1. Propose changes via RFC in `docs/governance/rfcs/`
2. ARB review and approval
3. Update this document
4. Announce to engineering teams
5. Update CI validation rules

---

## Related Documents

- [CONTRACT.md](../../contract.md) — Canonical contract definitions
- [DEPRECATIONS.md](../../DEPRECATIONS.md) — Human-readable deprecation list
- [deprecations.json](./deprecations.json) — Machine-readable deprecation register
- [Architecture Decision Records](../architecture/) — Historical context

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-04-28 | Platform Engineering | Initial policy creation per Contract Enforcement Fix Sprint |

---

**Questions?** Contact #architecture-support or architecture-review@company.com
