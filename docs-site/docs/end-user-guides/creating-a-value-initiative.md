---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Creating a Value Initiative

This guide walks you from a blank prospect account to a populated value model using the **Intelligence** and **Value Studio** workspaces. By the end, you will have captured signals, mapped value drivers, attached evidence, and built a quantified value model ready for business case generation.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- A signed-in session with access to a tenant workspace.
- Optional: a CRM connection for automatic account enrichment.
- Reviewed [Core Concepts: Initiatives](../core-concepts/initiatives.md).

## Step-by-step instructions

### 1. Create an account

1. From the left rail, open **Accounts**.
2. Click **New Account**, or use the **Prospect Prompt Builder** on the home page.
3. Enter the company name, industry, and estimated annual revenue.
4. Click **Create** and wait for the account overview to load.

!!! tip "Tip: Use the Prospect Prompt Builder for speed"
    Describe the account, buying context, and desired outcome in plain language. The system suggests signals and drivers automatically.

### 2. Capture Signals

1. Navigate to the account and select the **Intelligence** workspace.
2. Open the **Signals** tab.
3. Review ingested market signals and accept or reject each trigger.
4. For each accepted signal, add a note explaining why it matters to this account.

### 3. Enrich the account

1. Switch to the **Account Enrichment** tab.
2. Verify firmographics: company size, industry, annual revenue, and tech stack.
3. If data is missing, click **Refresh Enrichment** to pull from connected data sources.

### 4. Map Value Drivers

1. Open the **Value Drivers** tab.
2. Link validated signals to specific business value drivers.
3. For each driver, assign a category: `revenue_uplift`, `cost_savings`, or `risk_reduction`.
4. Set a priority: **Critical**, **High**, or **Medium**.

### 5. Attach Evidence

1. Open the **Evidence** tab.
2. Add verified evidence points that support each driver.
3. Upload documents, paste URLs, or link CRM records.
4. Mark evidence as **Validated** once it has been reviewed.

### 6. Map Stakeholders

1. Open the **Stakeholders** tab.
2. Click **Add Stakeholder** and enter name, role, and contact details.
3. Assign a buyer persona and set influence level: **Decision Maker**, **Influencer**, or **Blocker**.
4. Link stakeholders to the value drivers they care about.

### 7. Validate Hypotheses

1. Open the **Value Hypotheses** tab.
2. Review AI-generated hypotheses mapped to product capabilities.
3. Promote validated hypotheses and reject ones that do not fit.
4. For each promoted hypothesis, check the grounding label: **Evidence-backed**, **Assumption**, **Inference**, or **Fact**.

### 8. Build the Action Plan

1. Move to the **Value Studio** workspace.
2. Open the **Action Plan** tab.
3. Click **Generate Recommendations from Hypotheses**.
4. Review the generated recommendations and expand each to see:
   - Prospect Pain
   - Root Driver
   - Capability
   - Projected Value

### 9. Populate the Value Model

1. Switch to the **Value Model** tab.
2. Enter or confirm formula variables: `annual_revenue`, `employee_count`, `hours_saved_weekly`, `hourly_rate`, `implementation_cost`, `annual_license_cost`.
3. Add custom variables if needed.
4. The system evaluates each driver formula automatically.

### 10. Review the Driver Tree

1. Open the **Driver Tree** tab.
2. Visualize how individual drivers roll up to total portfolio value.
3. Drag to rearrange nodes or collapse branches.
4. Click any node to edit the underlying formula.

!!! tip "Tip: Use the ROI Calculator next"
    After populating the value model, open the **ROI Calculator** tab to compute simple ROI, payback period, and 3-year NPV.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Create / Edit | Assigned accounts |
| Admin | Configure data sources / Enable tabs | Tenant-wide |
| Executive | View / Approve | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum of **25 active value drivers** per account when using graph-backed resolution.
<span class="vp-badge vp-badge--limit">Limit</span> Signal ingestion is rate-limited by domain and plan tier.
<span class="vp-badge vp-badge--limit">Limit</span> Evidence uploads are limited to **50 MB per file**.

## Troubleshooting

??? question "Issue: No signals appear for a new account"
    **Cause:** The account has not been enriched or the ingestion job has not completed.
    **Resolution:** Wait for ingestion to finish, or manually trigger enrichment from the **Account Enrichment** tab. Check **Context Engine → Ingestion Jobs** for job status.

??? question "Issue: Value drivers show missing variables"
    **Cause:** Formula variables rely on enriched profile data that is incomplete.
    **Resolution:** Populate **annual_revenue**, **employee_count**, or custom variables in the account profile or the **Value Model** tab.

??? question "Issue: Hypotheses have low confidence"
    **Cause:** Few signals were accepted, or accepted signals lack evidence.
    **Resolution:** Return to the **Signals** tab, accept more signals, and attach evidence before regenerating hypotheses.

??? question "Issue: Cannot see the Driver Tree tab"
    **Cause:** The tab requires the `advanced` tier or a specific feature flag.
    **Resolution:** Ask your admin to verify your tier in **Workspace Settings → Team & Access → Roles**.

## Related pages

- [Building a Business Case](building-a-business-case.md)
- [Managing Stakeholders](managing-stakeholders.md)
- [Core Concepts: Initiatives](../core-concepts/initiatives.md)
- [Core Concepts: Value Metrics](../core-concepts/value-metrics.md)
- [Core Concepts: Benefits Tracking](../core-concepts/benefits-tracking.md)

## Escalation path

If account creation fails repeatedly, contact your workspace admin or open a support ticket with severity **P3** and the error message from the browser console.
