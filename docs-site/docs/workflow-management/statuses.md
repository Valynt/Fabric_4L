---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Workflow Statuses

Statuses represent the current state of a record. ValuePact uses a canonical set of statuses with configurable transitions so you can model your governance process precisely.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Analyst</span>
<span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Admin access to **Configuration** > **Workflows**
- Review of [Workflow Management overview](index.md)

## Canonical statuses

| Status | Meaning | Typical entry trigger |
|--------|---------|----------------------|
| `draft` | Record is being prepared | Manual creation |
| `in_review` | Under evaluation by approvers | User submission or automation |
| `approved` | Evaluation passed; ready to activate | Final approval stage complete |
| `rejected` | Evaluation failed; returned for revision | Approver rejection or guardrail failure |
| `active` | Work is underway | Activation by owner or automation |
| `completed` | Outcomes achieved and validated | User closure or milestone completion |
| `archived` | Retained for audit; read-only | Retention policy or manual archive |

## Status transitions

Transitions define valid movement between statuses. Each transition can be automatic or manual.

### Manual transitions

Manual transitions require a user with the correct role to click a button or call an API.

| From | To | Who can trigger | Required fields |
|------|-----|----------------|----------------|
| draft | in_review | Record owner, Analyst | Title, description, value metric |
| in_review | approved | Approver with `approve` permission | All approval stage gates passed |
| in_review | rejected | Approver with `reject` permission | Rejection reason |
| rejected | draft | Record owner | Updated fields addressing rejection |
| approved | active | Record owner, Admin | Start date, budget allocation |
| active | completed | Record owner, Admin | Actuals captured, evidence attached |
| completed | archived | Admin, automation | Retention period elapsed |

### Automatic transitions

Automatic transitions fire when conditions are met without user action.

| From | To | Trigger condition |
|------|-----|-------------------|
| draft | in_review | All required fields populated and auto-submit enabled |
| approved | active | Scheduled activation date reached |
| active | completed | All milestones marked complete and auto-close enabled |
| completed | archived | Retention policy duration exceeded |

!!! tip "Auto-submit"
    Enable auto-submit on the **Transitions** tab to let drafts move to `in_review` immediately when mandatory fields are complete.

## Transition matrix

|  | draft | in_review | approved | rejected | active | completed | archived |
|--|:-----:|:---------:|:--------:|:--------:|:------:|:---------:|:--------:|
| draft | — | Manual / Auto | — | — | — | — | — |
| in_review | — | — | Manual | Manual | — | — | — |
| approved | — | — | — | — | Manual / Auto | — | — |
| rejected | Manual | — | — | — | — | — | — |
| active | — | — | — | — | — | Manual / Auto | — |
| completed | — | — | — | — | — | — | Auto |
| archived | — | — | — | — | — | — | — |

## Step-by-step: add a custom status

1. Go to **Admin** > **Configuration** > **Workflows**.
2. Select the workflow and click **Edit**.
3. Click **Add Status**.
4. Enter a **Status Name** and **API Key**. Use `snake_case` for the key.
5. Choose a **Category**: `open`, `pending`, `closed`, or `terminal`.
6. Set **Color** and **Icon** for visual identification in boards and lists.
7. Click **Save**, then **Publish**.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Create, edit, delete statuses | Organization |
| Tenant Admin | Create, edit, delete statuses | Organization |
| Content Admin | Edit status display properties | Organization |
| Analyst | Transition records they own | Own records |
| Editor | Transition records in their group | Group-assigned records |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> You cannot delete a status that is in use by active records. Archive it instead.

<span class="vp-badge vp-badge--limit">Limit</span> Status API keys must be unique within a workflow and cannot exceed 40 characters.

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 20 inbound and 20 outbound transitions per status is enforced.

<span class="vp-badge vp-badge--limit">Limit</span> Terminal statuses cannot have outbound transitions.

## Troubleshooting

??? question "Issue: status does not appear in the dropdown"
    **Cause:** The status is saved but the workflow is not published, or the status category is hidden in the current view filter.
    **Resolution:** Publish the workflow. Check the board or list filter settings to ensure the category is visible.

??? question "Issue: automatic transition did not fire"
    **Cause:** The automation rule is disabled, or a guard condition failed silently.
    **Resolution:** Open **Automation** and verify the rule is active. Review the rule execution log for guard failures.

??? question "Issue: record stuck in a loop between two statuses"
    **Cause:** Two automatic transitions reference each other without an exit condition.
    **Resolution:** Add a condition or manual gate to break the loop. Use the workflow diagram to visualize cycles.

## Related pages

- [Workflow Management Overview](index.md)
- [Lifecycle Management](lifecycle-management.md)
- [Approval Workflows](approval-workflows.md)
- [Automation](automation.md)

## Escalation path

For status-transition logic errors that affect data integrity:

1. Document the record ID, expected transition, and actual behavior.
2. File a support ticket with severity **Medium**.
3. If multiple tenants are affected, escalate via `#valuepact-ops` with the `incident` label.
