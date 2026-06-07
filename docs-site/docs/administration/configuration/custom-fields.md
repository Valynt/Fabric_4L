---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Custom Fields

Custom fields extend the ValuePact data model to capture information unique to your organization. You define the field type, validation rules, and display logic.

## Who this is for

<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Analyst</span>

## Prerequisites

- Tenant Admin or Content Admin role
- Review of [Configuration Overview](index.md)
- Understanding of the entity you are extending (Initiative, Business Case, etc.)

## Field types

| Type | Use case | Validation options |
|------|----------|-------------------|
| Text | Free-form names, descriptions | Min/max length, regex pattern |
| Number | Quantities, scores | Min/max value, decimal places |
| Date | Deadlines, milestones | Min/max date, business days only |
| Select | Categories, priorities | Single or multi-select, option list |
| User | Assignee, stakeholder | Restrict to role or group |
| Formula | Calculated values | Expression editor, output format |

## Step-by-step: add a custom field

1. Go to **Admin** > **Configuration** > **Custom Fields**.
2. Select the **Entity Type**: Initiative, Business Case, or Stakeholder.
3. Click **Add Field**.
4. Enter a **Field Label** and **API Key**. Use `snake_case` for the key.
5. Choose a **Field Type**.
6. Set **Validation Rules**.
7. Configure **Display Rules** (when the field is visible or required).
8. Click **Save** and **Publish**.

!!! warning "API key immutability"
    The API key cannot be changed after creation. Choose it carefully if you plan to use it in integrations or formulas.

## Validation rules

Validation rules ensure data quality at entry time.

| Rule | Description | Example |
|------|-------------|---------|
| Required | Field must be populated before saving | Budget is mandatory |
| Unique | Value must be unique across the tenant | Project code |
| Regex | Value must match a regular expression | SKU format |
| Range | Number or date must fall within bounds | Budget between 10k and 10M |

## Display rules

Display rules control when a field appears or becomes required.

1. Open the custom field editor.
2. Click **Display Rules**.
3. Add a condition: `When [Field] [Operator] [Value]`.
4. Set the action: **Show**, **Hide**, **Require**, or **Optional**.
5. Click **Save**.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Super Admin | Create, edit, delete custom fields | Organization |
| Tenant Admin | Create, edit, delete custom fields | Organization |
| Content Admin | Create, edit custom fields | Organization |
| Analyst | View and edit custom fields on assigned records | Assigned records |
| Viewer | View custom fields on assigned records | Assigned records |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 100 custom fields per entity type.

<span class="vp-badge vp-badge--limit">Limit</span> API keys must be unique within the tenant and cannot exceed 40 characters.

<span class="vp-badge vp-badge--limit">Limit</span> Formula fields can reference up to 10 other fields.

<span class="vp-badge vp-badge--limit">Limit</span> Display rule conditions support up to 3 nested clauses.

## Troubleshooting

??? question "Issue: custom field not visible on record"
    **Cause:** A display rule is hiding it, or the field was added to a different entity type.
    **Resolution:** Check the display rule conditions. Confirm the field belongs to the entity you are viewing.

??? question "Issue: validation error on a correct value"
    **Cause:** The regex or range was updated after existing records were created, or the rule contains a syntax error.
    **Resolution:** Review the validation rule in **Custom Fields**. Test the rule against the value in the preview panel.

## Related pages

- [Configuration Overview](index.md)
- [Workflows](workflows.md)
- [Branding](branding.md)
- [Notifications](notifications.md)

## Escalation path

For custom field corruption or formula evaluation errors:

1. Disable the field from the entity form to prevent further bad data.
2. Review the formula or validation rule for syntax issues.
3. File a support ticket with the field API key and an example record ID.
4. Escalate to `#valuepact-ops` if the field is used in a production workflow.
