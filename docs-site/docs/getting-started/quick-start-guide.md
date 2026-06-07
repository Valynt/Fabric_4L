---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Quick Start Guide

This guide walks you through a complete end-to-end workflow: signing in, touring the platform, selecting an account, building intelligence, creating a value model, generating a business case, and exporting your first report.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- [ ] An invitation to a ValuePact workspace (Clerk organization).
- [ ] A confirmed email address and active SSO or password-based session.
- [ ] At least one prospect account created or shared with you.

!!! note
    If your organization uses SSO, you must complete SSO setup before your first sign-in. Ask your admin for the SSO provider name (Okta, Azure AD, Google Workspace, etc.).

## Step-by-step instructions

### Step 1: Sign in and choose a workspace

1. Navigate to your ValuePact tenant URL (for example, `https://app.valuepact.ai`).
2. Click **Sign in** and authenticate via Clerk (password, magic link, or SSO).
3. If you belong to multiple organizations, the **Choose a workspace** screen appears. Select the organization you want to work in.
4. You land on the **Command Center** dashboard.

!!! warning
    Do not share your Clerk session or MFA codes. ValuePact ties every action to your authenticated identity and tenant context.

### Step 2: Select a prospect account

1. In the **left rail**, click **Accounts**.
2. Browse the account list or use the **Search** bar to filter by name or industry.
3. Click an account card to select it. The platform scopes all subsequent workspaces to this account.

!!! tip
    If no accounts exist, click **New Account** and fill in **Account Name**, **Industry**, and **Tier**. Only users with the **User** role or higher can create accounts.

### Step 3: Gather intelligence

1. In the **left rail**, click **Intelligence**. The workspace loads with horizontal tabs:
   - **Signals**
   - **Drivers**
   - **Evidence**
   - **Stakeholders**
2. Click **Signals** to view detected pain signals and opportunities.
3. Review confidence scores. High-confidence signals display without badges; low-confidence signals show a **low-confidence** warning badge.
4. Click **Drivers** to see weighted value drivers (for example, Operational Efficiency at 0.45, Cost Reduction at 0.35).
5. Click **Evidence** to review supporting claims and their source documents.
6. Click **Stakeholders** to view mapped contacts and their influence levels.

!!! tip
    Use the **Agent Chat** in the right rail to ask questions like *"What is the highest-confidence signal?"* The agent synthesizes data across tabs with full traceability.

### Step 4: Build the value model in Value Studio

1. In the **left rail**, click **Value Studio**. The workspace loads three tabs:
   - **Action Plan**
   - **Value Model**
   - **Narrative**
2. Click **Action Plan** to review prioritized initiatives, timelines, and owners.
3. Click **Value Model** to inspect variables, formulas, and ROI calculations.
4. Edit a variable value (for example, **Annual Revenue**) and observe the formula recalculation in real time.
5. Click **Narrative** to read the auto-generated executive summary and value proposition.

!!! warning
    Invalid formula values trigger a validation error. If you enter a value outside the supported range, the platform returns a `422` error and displays a **validation-error** indicator.

### Step 5: Generate a business case

1. In the **left rail**, click **Deliverables**.
2. Click **Business Cases** to view existing cases or click **Generate Business Case**.
3. The Layer 4 **Business Case Generator** agent populates the case from your Value Studio data.
4. Review the case title, total value, and status.
5. Submit the case for approval if your workflow requires it.

!!! note
    Draft business cases cannot be exported. The **Export** button is disabled until the status changes to **approved**.

### Step 6: Export and share

1. Open an approved business case.
2. Click **Export** and select a format:
   - **CFO View** — financial summary with ROI and payback period.
   - **Executive View** — strategic narrative with key outcomes.
   - **Technical View** — implementation roadmap and dependencies.
3. Download the PDF or copy a shared link.

### Step 7: Review governance

1. In the **left rail**, click **Governance**.
2. Click **Audit Log** to see every action taken on the account.
3. Click **Traces** to view decision provenance chains linking agent outputs to source documents.
4. Click **Health** to verify system component statuses.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Create accounts | Organization |
| User | Edit value model variables | Assigned accounts |
| User | Generate business cases | Assigned accounts |
| Admin | Approve business cases | Organization |
| Admin | Activate value packs | Organization |
| Viewer | View intelligence and deliverables | Assigned accounts |
| Viewer | Cannot edit or export | Assigned accounts |

<span class="vp-badge vp-badge--permission">Required</span> Business case export requires **approved** status. Draft exports are blocked for all roles.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> You can create up to 100 prospect accounts per organization.

<span class="vp-badge vp-badge--limit">Limit</span> Each business case supports a maximum of 50 variables and 20 formulas.

<span class="vp-badge vp-badge--limit">Limit</span> Agent stream messages are limited to 4,000 characters per input.

<span class="vp-badge vp-badge--limit">Limit</span> Export generation timeout: 60 seconds. Large cases may take longer; retry if the download fails.

## Troubleshooting

??? question "Issue: I cannot see the Intelligence or Value Studio tabs"
    **Cause:** No prospect account is selected.
    **Resolution:** Return to **Accounts** and select an account. The left rail items **Intelligence**, **Value Studio**, and **Deliverables** are scoped to an active account selection.

??? question "Issue: The Export button is disabled"
    **Cause:** The business case status is **draft**.
    **Resolution:** Submit the case for approval. An **Admin** or **Executive** must approve it before export is enabled.

??? question "Issue: Agent chat returns an error state"
    **Cause:** The Layer 4 agent runtime is temporarily unavailable, or the request exceeded the token limit.
    **Resolution:** Wait 30 seconds and retry. If the error persists, check **Governance** > **Health** for agent runtime status and open a support ticket if degraded.

??? question "Issue: I was redirected to /sign-in while working"
    **Cause:** Your Clerk session expired or the organization context was lost.
    **Resolution:** Sign in again. If using SSO, ensure your identity provider session is active.

??? question "Issue: Cross-tenant data appears in search results"
    **Cause:** This should never happen; tenant isolation is enforced at every layer.
    **Resolution:** Do not interact with the data. Immediately report to your admin and open a severity **S1** security ticket.

## Related pages

- [What is ValuePact?](what-is-valuepact.md)
- [Navigating the Platform](navigating-the-platform.md)
- [User Roles](user-roles.md)
- [Core Concepts: Initiatives](../core-concepts/initiatives.md)
- [Core Concepts: Business Cases](../core-concepts/business-cases.md)
- [Core Concepts: Value Metrics](../core-concepts/value-metrics.md)
- [End-User Guides: Creating a Value Initiative](../end-user-guides/creating-a-value-initiative.md)
- [End-User Guides: Building a Business Case](../end-user-guides/building-a-business-case.md)

## Escalation path

If you are blocked during onboarding:

1. Verify your role and permissions on the [User Roles](user-roles.md) page.
2. Ask your organization admin to confirm you are added to the correct Clerk organization.
3. For SSO or MFA issues, see [Administration: SSO](../administration/security/sso.md) or [Administration: MFA](../administration/security/mfa.md).
4. Open a support ticket with severity **S3** and include the account name, workspace, and the step where you are stuck.
