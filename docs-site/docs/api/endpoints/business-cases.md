---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Business Cases API

Create, manage, and export business cases — packaged value arguments built from initiatives and value models.

## Who this is for

<span class="vp-badge vp-badge--role">Developer</span>
<span class="vp-badge vp-badge--role">Admin</span>

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/business-cases` | List business cases |
| POST | `/v1/business-cases` | Create a business case |
| GET | `/v1/business-cases/{id}` | Get a business case |
| PUT | `/v1/business-cases/{id}` | Update a business case |
| POST | `/v1/business-cases/{id}/approve` | Approve a business case |
| POST | `/v1/business-cases/{id}/export` | Export to PDF |
| DELETE | `/v1/business-cases/{id}` | Delete a business case |

## Create a business case

```http
POST /v1/business-cases
Content-Type: application/json

{
  "initiative_id": "init_abc123",
  "name": "Cloud Migration ROI Analysis",
  "template": "executive_summary",
  "sections": [
    "executive_summary",
    "financial_analysis",
    "risk_assessment",
    "implementation_roadmap"
  ]
}
```

**Templates:** `executive_summary`, `cfo_view`, `technical_deep_dive`, `board_presentation`

## Approve a business case

```http
POST /v1/business-cases/bc_def456/approve
Content-Type: application/json

{
  "approval_level": "executive",
  "notes": "Approved with contingency reserve of 15%"
}
```

!!! warning "Approval is irreversible"
    Once approved, a business case enters a locked state. Create a new version for revisions.

## Export a business case

```http
POST /v1/business-cases/bc_def456/export
Content-Type: application/json

{
  "format": "pdf",
  "include_appendices": true,
  "watermark": "CONFIDENTIAL"
}
```

**Formats:** `pdf`, `docx`, `pptx`

## Permissions

| Action | Required Permission |
|--------|---------------------|
| List | `business_cases:read` |
| Create | `business_cases:write` |
| Approve | `business_cases:approve` |
| Export | `business_cases:read` |
| Delete | `business_cases:write` |

## Limits

<span class="vp-badge vp-badge--limit">Limit</span> Maximum 50 business cases per initiative.

<span class="vp-badge vp-badge--limit">Limit</span> Export processing time: up to 60 seconds for large cases.

## Troubleshooting

??? question "Approval fails with 409"
    **Cause**: Business case is missing required sections or has unresolved validation errors.
    **Resolution**: Review the business case completeness check and resolve all flagged items before submitting for approval.

??? question "Export times out"
    **Cause**: Business case includes too many large embedded assets.
    **Resolution**: Reduce image sizes or split into multiple exports. Contact support for enterprise export limits.

## Related pages

- [API Overview](../overview.md)
- [Core Concepts → Business Cases](../../core-concepts/business-cases.md)
- [End User Guides → Building a Business Case](../../end-user-guides/building-a-business-case.md)
