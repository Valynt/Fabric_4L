---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Business Cases

A business case is a packaged, defensible value argument that translates value models into stakeholder-ready deliverables. It includes an executive summary, financial analysis, risk assessment, and evidence-backed claims.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Executive</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Prerequisites

- A ValuePact account with completed [value hypotheses](opportunities.md) or a [value model](roi-calculations.md)
- At least one [ROI calculation](roi-calculations.md) for the account
- Role permission to generate or approve deliverables

## Overview

Business cases are produced in the **Deliverables** workspace. The platform uses Layer 4 agentic workflows to auto-generate drafts from value models, hypotheses, and evidence. Human reviewers validate claims before the case is published.

Each business case carries:

- **Executive summary** — one-page narrative tailored to the economic buyer
- **Current state** — documented pain points and baseline metrics
- **Proposed solution** — capabilities mapped to outcomes
- **Financial analysis** — NPV, IRR, payback period, and ROI percentage
- **Risk mitigation** — identified risks with mitigation strategies
- **Evidence appendix** — linked sources, confidence scores, and provenance

## How it works

### Generate a draft

1. Open the account's **Deliverables** workspace.
2. Click **Generate Business Case**.
3. Select the target audience: CFO, executive, or technical.
4. Choose the scenario baseline: conservative, expected, or optimistic.
5. Click **Generate**. The Layer 4 Business Case workflow compiles the document.

The workflow retrieves the account's value tree, evaluates formulas, pulls evidence from the Evidence Library, and writes each section using structured generation.

### Review and validate

Generated claims are checked against the Ground Truth validation state machine:

| Status | Meaning | Action required |
|--------|---------|----------------|
| Extracted | AI-structured from source | Review for accuracy |
| Supported | Linked to at least one evidence source | Validate source relevance |
| Corroborated | Two or more independent sources | Fast-track approval |
| Approved | Human-validated | Ready for publication |

### Publish and share

Once approved, the business case can be exported as Markdown, DOCX, PDF, or PPTX. Sharing links are tenant-scoped and expire after 30 days by default.

### Versioning and audit trail

Every business case maintains a version history:

- **Draft versions** — auto-saved every 5 minutes during editing
- **Published versions** — immutable snapshots tied to approval events
- **Amendments** — tracked changes after initial publication

The audit trail records who generated, reviewed, approved, and exported each version. Audit logs are retained for 7 years and are accessible via **Governance > Audit Log**.

### Evidence quality gates

Before a business case can be submitted for review, it must pass evidence quality gates:

| Gate | Requirement | Failure behavior |
|------|-------------|------------------|
| Minimum evidence | At least 3 evidence items linked | Warning, not blocking |
| Confidence threshold | Average claim confidence ≥ 0.6 | Warning, not blocking |
| Source diversity | At least 2 distinct source types | Blocking for CFO view |
| Ground Truth alignment | All material claims have a TruthObject | Blocking for executive view |

## Deliverable views

| View | Content focus | Best for |
|------|--------------|----------|
| CFO view | Financial metrics, sensitivity analysis, benchmark comparison | Finance approvers |
| Executive view | Strategic narrative, risk mitigation, competitive positioning | C-suite presentations |
| Technical view | Capability mapping, implementation roadmap, integration requirements | Engineering evaluators |

## Approval flows

Business cases move through a standard review workflow:

```
DRAFT → NEEDS_REVIEW → APPROVED → PUBLISHED
   ↓         ↓            ↓
REJECTED  MODIFIED     ARCHIVED
```

- **DRAFT** — Initial auto-generated state
- **NEEDS_REVIEW** — Submitted for human validation
- **APPROVED** — Reviewer accepts claims and financials
- **PUBLISHED** — Shared with external stakeholders
- **REJECTED** — Returned to draft with reviewer notes
- **MODIFIED** — Published case edited after feedback

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure approval workflows | Organization |
| User | Generate and edit drafts | Assigned accounts |
| User | Submit for review | Assigned accounts |
| Executive | Approve or reject | Organization or assigned accounts |

<span class="vp-badge vp-badge--permission">Required</span> `deliverables:write` to generate; `deliverables:approve` to publish.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Business case generation is limited to 10 drafts per account per hour.

<span class="vp-badge vp-badge--limit">Limit</span> Exported documents have a maximum size of 50 MB.

<span class="vp-badge vp-badge--limit">Limit</span> Claims with confidence below 0.6 are flagged but not blocked from inclusion.

## Troubleshooting

??? question "Issue: Business case generation fails with 'insufficient evidence'"
    **Cause:** The account has fewer than three linked evidence items for the selected value drivers.
    **Resolution:** Add evidence in the **Intelligence** workspace under the **Evidence** tab, then regenerate.

??? question "Issue: CFO view shows blank sensitivity table"
    **Cause:** The ROI calculation was run without enabling sensitivity analysis.
    **Resolution:** Return to **Value Studio**, open the ROI calculator, toggle **Sensitivity Analysis**, and recalculate.

??? question "Issue: Approval workflow is stuck in 'needs_review'"
    **Cause:** No user with `deliverables:approve` permission has been assigned as a reviewer.
    **Resolution:** Ask an admin to assign an approver in **Administration > Workflows > Business Case Approval**.

??? question "Issue: Exported PDF is missing charts"
    **Cause:** The chart generation service timed out or the sensitivity analysis was not run.
    **Resolution:** Re-run the ROI calculation with sensitivity analysis enabled, wait for chart generation to complete, and re-export.

## Related pages

- [ROI Calculations](roi-calculations.md)
- [Value Realization](value-realization.md)
- [Stakeholders](stakeholders.md)
- [Outcomes](outcomes.md)

## Escalation path

For generation failures or workflow misconfiguration, contact your workspace admin. For suspected agent hallucinations, follow the [Investigate Hallucinated Business Case](../fabric4l/operations/runbooks.md) runbook.