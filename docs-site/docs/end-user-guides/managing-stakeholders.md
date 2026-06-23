---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Managing Stakeholders

Map buyer personas, track influence, and link stakeholders to value drivers in the **Intelligence** workspace. Effective stakeholder management ensures your business case speaks to the right people with the right messages.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- An existing account with enriched data.
- Reviewed [Core Concepts: Stakeholders](../core-concepts/stakeholders.md).
- Optional: configured buyer personas for your tenant.

## Step-by-step instructions

### 1. Open the Stakeholders tab

1. Navigate to the account and select the **Intelligence** workspace.
2. Click the **Stakeholders** tab.
3. If no stakeholders exist, the page shows an empty state with an **Add Stakeholder** button.

### 2. Add stakeholders

1. Click **Add Stakeholder**.
2. Enter the following fields:
   - **Name**
   - **Role** (for example, CFO, VP Engineering, Procurement Lead)
   - **Contact email**
   - **Phone** (optional)
3. Click **Save**.

### 3. Map personas

1. In the stakeholder detail panel, open the **Persona** dropdown.
2. Select a buyer persona. Options map to your tenant’s configured personas.
3. Common personas include:
   - Economic Buyer
   - Technical Champion
   - End User
   - Compliance Officer

### 4. Set influence level

1. Mark each stakeholder as one of:
   - **Decision Maker** — can approve or reject the initiative.
   - **Influencer** — shapes the decision but does not own the budget.
   - **Blocker** — can stop the initiative if concerns are not addressed.
2. The influence level appears as a badge on the stakeholder card.

### 5. Link to value drivers

1. In the stakeholder detail panel, open the **Linked Drivers** section.
2. Click **Link Driver** and select from the account’s validated value drivers.
3. Add a note explaining why this driver matters to the stakeholder.
4. Linked drivers appear in audience-specific business case views.

### 6. Track engagement

1. Use the **Engagement Timeline** to log meetings, emails, and discovery notes.
2. Click **Add Activity** and choose a type:
   - Meeting
   - Email
   - Call
   - Discovery Session
3. Add a summary and attach files if needed.
4. Activities are visible to all users with access to the account.

### 7. Validate persona fit

1. Switch to the **Persona Fit** tab.
2. See how well the account matches ideal buyer profiles.
3. Review fit scores for each persona and identify gaps.
4. Use gaps to shape discovery questions and value messaging.

### 8. Export the stakeholder map

1. Click **Export** in the **Stakeholders** tab.
2. Choose format: PDF or CSV.
3. Share the map with account teams or leadership.

!!! tip "Tip: Link stakeholders before building the business case"
    Stakeholder-linked value drivers appear in the **Executive View** under Strategic Recommendations, tailored by persona. This makes the case more persuasive.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Create / Edit / Link | Assigned accounts |
| Admin | Configure personas / Delete any | Tenant-wide |
| Executive | View / Export | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum of **50 stakeholders** per account.
<span class="vp-badge vp-badge--limit">Limit</span> Engagement logs are retained for **24 months**.
<span class="vp-badge vp-badge--limit">Limit</span> Each stakeholder can be linked to up to **10 value drivers**.
<span class="vp-badge vp-badge--limit">Limit</span> Persona fit scores are recalculated nightly.

## Troubleshooting

??? question "Issue: Persona dropdown is empty"
    **Cause:** No personas have been configured for the tenant.
    **Resolution:** Ask an admin to configure personas in **Workspace Settings → Data & Integrations → Value Packs**.

??? question "Issue: Stakeholder does not appear in business case"
    **Cause:** The stakeholder was not linked to a value driver that appears in the generated narrative.
    **Resolution:** Edit the stakeholder and add at least one linked driver with validated evidence. Regenerate the business case if needed.

??? question "Issue: Cannot add engagement activity"
    **Cause:** The stakeholder record was created by another user and you lack edit permissions.
    **Resolution:** Ask the stakeholder owner or an admin to adjust permissions in **Workspace Settings → Team & Access → Permissions**.

??? question "Issue: Export is missing some stakeholders"
    **Cause:** The export filter is scoped to active stakeholders only.
    **Resolution:** Check the filter toggle and include archived or inactive stakeholders if needed.

??? question "Issue: Persona fit score seems inaccurate"
    **Cause:** The account enrichment data is incomplete or outdated.
    **Resolution:** Refresh enrichment from the **Account Enrichment** tab and wait for the next nightly recalculation.

## Related pages

- [Creating a Value Initiative](creating-a-value-initiative.md)
- [Building a Business Case](building-a-business-case.md)
- [Core Concepts: Stakeholders](../core-concepts/stakeholders.md)
- [Collaboration](collaboration.md)

## Escalation path

For bulk import requests or persona configuration issues, contact your admin or open a support ticket with severity **P4**.
