---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Building a Business Case

Use **Value Studio** to assemble validated intelligence into a packaged, defensible business case. Then generate audience-specific views for executive, CFO, and technical stakeholders. This guide covers generation, validation, trust review, export, and post-approval actions.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- A populated value model with validated drivers and evidence.
- Completed ROI calculation in the **ROI Calculator** tab.
- Reviewed [Creating a Value Initiative](creating-a-value-initiative.md).
- Reviewed [Core Concepts: Business Cases](../core-concepts/business-cases.md).

## Step-by-step instructions

### 1. Author the narrative

1. In **Value Studio**, select the **Narrative** tab.
2. Write the value story using the structured editor.
3. Reference specific value drivers and evidence IDs to keep claims traceable.
4. Save drafts frequently. The system autosaves every 30 seconds.

### 2. Generate the Executive Value Case

1. Switch to the **Executive Value Case** tab.
2. Click **Generate Value Case** to trigger the Layer 4 agent workflow.
3. The workflow gathers inputs, runs the ROI sub-workflow, generates narrative sections, validates claims against Layer 5, and assembles the document.
4. Wait for the status to change from **Pending** to **Completed**.

### 3. Review trust status

Check the trust state banner at the top of the case:

| Trust State | Meaning | Can Export? |
|-------------|---------|-------------|
| **Export Ready** | Validated and document generated | Yes |
| **Validated** | Approved but no document yet | No — generate first |
| **Pending Review** | Claims need validation or human approval | No |
| **Export Blocked** | Failed or rejected status | No |
| **Degraded** | LLM, validation, or evidence enrichment incomplete | No — internal draft only |

!!! warning "Warning: Do not export degraded cases"
    Degraded cases are marked **Internal draft only**. Claims may be unverified or missing evidence references. Complete validation before sharing externally.

### 4. Inspect claim validation

1. Review the **Claim Validation** badge on the business case detail page.
2. States include:
   - `Validated` — all claims passed.
   - `Partial` — some claims passed.
   - `Failed` — claims did not meet truth requirements.
3. Open **Claim Traceability** to see each claim linked to evidence, benchmarks, or assumptions.

### 5. Export the business case

1. Click **Export PDF** from the action bar.
2. Wait for the export job. A download link appears when ready.
3. The link expires after **72 hours**.

### 6. Open audience views

Navigate to **Deliverables** and choose a view:

=== "Executive View"
    - Strategic alignment summary
    - High-level ROI and payback
    - Decision confidence gauge
    - Recommended next steps

=== "CFO View"
    - Financial KPIs: Total Value, ROI, Payback, Confidence
    - Cost-Benefit Summary table
    - Key Recommendations
    - Risk & Remediation Items

=== "Technical View"
    - Document metadata (pages, file size)
    - Evidence Provenance Chain
    - Case Metadata grid
    - Technical Remediation Items

### 7. Push to CRM (optional)

1. After approval, scroll to the **Post-Approval Actions** section.
2. If **CRM Push** shows ready, click **Push to CRM**.
3. The case is sent as a renewal or expansion proof package.

### 8. Convert to Value Realization (optional)

1. After approval, click **Convert to Value Realization**.
2. The system creates a realization plan with baselines and milestones.
3. You can now enter actuals and track variance over time.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Generate / Export | Assigned accounts |
| Admin | Regenerate / Push CRM / Convert realization | Tenant-wide |
| Executive | Approve / View all / Export portfolio | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Claim validation is capped at **20 claims per run**.
<span class="vp-badge vp-badge--limit">Limit</span> PDF exports expire after **72 hours** if not downloaded.
<span class="vp-badge vp-badge--limit">Limit</span> Business case generation is limited to **5 concurrent workflows** per tenant.

## Troubleshooting

??? question "Issue: Export PDF button is disabled"
    **Cause:** The business case status is not approved or the document has not been generated.
    **Resolution:** Wait for the workflow to complete, or click **Regenerate Business Case** if the account data has changed. Verify the trust state is **Export Ready**.

??? question "Issue: Trust state shows Degraded"
    **Cause:** Unverified claims, missing tenant context, or LLM failure during generation.
    **Resolution:** Open **Claim Traceability** to inspect unverified claims. Add evidence or rerun validation. If the issue persists, check the **Governance → Traces** tab for workflow errors.

??? question "Issue: CRM Push is disabled"
    **Cause:** The case is not approved, or export metadata is not ready.
    **Resolution:** Ensure the trust state is **Export Ready** and the **Post-Approval Actions** card shows CRM Push as available.

??? question "Issue: Regeneration produces identical content"
    **Cause:** The value model and hypotheses have not changed since the last run.
    **Resolution:** Update the **Value Model** tab or accept new signals before regenerating.

## Related pages

- [Creating a Value Initiative](creating-a-value-initiative.md)
- [Tracking Benefits](tracking-benefits.md)
- [Core Concepts: Business Cases](../core-concepts/business-cases.md)
- [Core Concepts: ROI Calculations](../core-concepts/roi-calculations.md)
- [Exporting & Sharing Reports](../dashboards-reporting/exporting-sharing-reports.md)

## Escalation path

If regeneration loops fail or CRM push returns errors, contact support with the **case_id** and severity **P2**.
