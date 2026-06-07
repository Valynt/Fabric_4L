---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# User Guides

These guides teach you how to complete end-to-end value workflows in ValuePact. Each guide maps to a real workspace, tab, or deliverable in the platform. Work through them in order or jump to the topic you need.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Recommended learning path

- [ ] **Beginner** — Start with [Creating a Value Initiative](creating-a-value-initiative.md) to build your first account and value model.
- [ ] **Intermediate** — Move to [Building a Business Case](building-a-business-case.md) to package intelligence into a CFO-ready deliverable.
- [ ] **Advanced** — Explore [Tracking Benefits](tracking-benefits.md) and [Managing Stakeholders](managing-stakeholders.md) to operationalize value realization.
- [ ] **Collaboration** — Learn [Collaboration](collaboration.md) to work with teammates using comments, tasks, approvals, and version history.

## Guide map

| Guide | Workspace | What you will learn | Time |
|-------|-----------|---------------------|------|
| [Creating a Value Initiative](creating-a-value-initiative.md) | Intelligence → Value Studio | From blank account to a populated value model with drivers and evidence | 20 min |
| [Building a Business Case](building-a-business-case.md) | Value Studio → Deliverables | Generate, validate, and export a business case with audience-specific views | 25 min |
| [Tracking Benefits](tracking-benefits.md) | Value Studio → Governance | Set baselines, enter actuals, and monitor variance against forecasts | 15 min |
| [Managing Stakeholders](managing-stakeholders.md) | Intelligence | Map influence, track engagement, and link stakeholders to value drivers | 15 min |
| [Collaboration](collaboration.md) | Cross-workspace | Comments, mentions, approvals, sharing, and version history | 10 min |

## How the guides connect

```
Intelligence workspace
  ├── Signals → Drivers → Evidence → Stakeholders
  └── (guides: Creating a Value Initiative, Managing Stakeholders)

Value Studio workspace
  ├── Action Plan → Value Model → Narrative → Calculator
  └── (guides: Creating a Value Initiative, Building a Business Case, Tracking Benefits)

Deliverables workspace
  ├── Business Case → Executive View → CFO View → Technical View
  └── (guides: Building a Business Case)

Governance workspace
  ├── Audit trail → Provenance → Compliance
  └── (guides: Tracking Benefits, Collaboration)
```

## Role-based entry points

=== "End User"
    Start with [Creating a Value Initiative](creating-a-value-initiative.md). You will build an account, capture signals, map drivers, and populate a value model. After that, move to [Building a Business Case](building-a-business-case.md) to package your work.

=== "Admin"
    Review [Collaboration](collaboration.md) first to understand tenant-wide sharing and approval settings. Then read [Managing Stakeholders](managing-stakeholders.md) to configure personas and engagement tracking.

=== "Executive"
    Skip to [Building a Business Case](building-a-business-case.md) and [Tracking Benefits](tracking-benefits.md). You will learn how to read trust states, approve cases, and monitor realization at the portfolio level.

## Prerequisites

- A ValuePact workspace invitation and an active session.
- Familiarity with the [Quick Start Guide](../getting-started/quick-start-guide.md).
- Understanding of [Core Concepts](../core-concepts/index.md) such as value drivers, ROI, and realization.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Read guides / Execute workflows | Assigned accounts |
| Admin | Configure guide scope / Enable features | Tenant-wide |
| Executive | Read all guides / Approve deliverables | Portfolio |

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> Some tabs (for example, **Value Ontology**, **Alternatives**, **Solution Cost**) are feature-flagged and may not be visible in your tenant.
<span class="vp-badge vp-badge--limit">Limit</span> The Prospect Prompt Builder is available on the home page for users with the `standard` tier or higher.
<span class="vp-badge vp-badge--limit">Limit</span> Business case generation requires at least one validated value driver.

## Troubleshooting

??? question "Issue: A guide references a tab I cannot see"
    **Cause:** The tab is behind a feature flag or requires an advanced tier.
    **Resolution:** Contact your admin to verify tenant settings in **Workspace Settings → Data & Integrations**.

??? question "Issue: Workspace navigation differs from the guide"
    **Cause:** Your tenant uses a custom navigation schema or branding override.
    **Resolution:** Check **Workspace Settings → Branding** or ask your admin for the canonical path.

??? question "Issue: Guide links return 404"
    **Cause:** The documentation site is not fully synced with your tenant version.
    **Resolution:** Check the release notes for feature availability, or contact support for the correct page path.

## Related pages

- [Quick Start Guide](../getting-started/quick-start-guide.md)
- [Core Concepts](../core-concepts/index.md)
- [Navigating the Platform](../getting-started/navigating-the-platform.md)
- [Dashboards & Reporting Overview](../dashboards-reporting/index.md)
- [Analytics Overview](../analytics/index.md)

## Escalation path

If a guide step fails repeatedly across multiple accounts, open a support ticket with severity **P3** and include the account ID, workspace name, and tab ID.
