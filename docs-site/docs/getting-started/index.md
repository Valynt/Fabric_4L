---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Getting Started

This section takes you from your first sign-in to your first defensible business case in ValuePact. You will learn the platform layout, choose the right learning path for your role, and complete a guided end-to-end workflow.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Overview

ValuePact is a B2B SaaS platform for value realization. Teams use it to define, forecast, track, and report business value across initiatives, projects, stakeholders, and outcomes. The documentation in this section is designed to be read in order or jumped to based on your immediate need.

## Learning paths

Choose the path that matches your goal:

=== "I am new to ValuePact"

    1. Read [What is ValuePact?](what-is-valuepact.md) to understand the product and architecture.
    2. Follow the [Quick Start Guide](quick-start-guide.md) to sign in, tour the platform, and build your first business case.
    3. Review [User Roles](user-roles.md) to understand what you can see and do.

=== "I need to onboard my team"

    1. Start with [User Roles](user-roles.md) to decide who gets viewer, user, admin, or executive access.
    2. Read the [Quick Start Guide](quick-start-guide.md) to validate the workflow before inviting others.
    3. Explore [Administration](../administration/index.md) for user management, SSO, and branding.

=== "I want to understand the UI"

    1. Jump to [Navigating the Platform](navigating-the-platform.md) for a complete anatomy of the left rail, workspaces, right rail, and status indicators.
    2. Return to the [Quick Start Guide](quick-start-guide.md) for hands-on practice.

=== "I am an executive"

    1. Read [What is ValuePact?](what-is-valuepact.md) for the value proposition and high-level capabilities.
    2. Review [User Roles](user-roles.md) to understand the executive role and permissions.
    3. Explore [Dashboards & Reporting](../dashboards-reporting/index.md) for portfolio and executive views.

## What to read first

| If you want to... | Read this first |
|---|---|
| Understand what ValuePact does | [What is ValuePact?](what-is-valuepact.md) |
| Get hands-on immediately | [Quick Start Guide](quick-start-guide.md) |
| Know what your role allows | [User Roles](user-roles.md) |
| Find your way around the UI | [Navigating the Platform](navigating-the-platform.md) |
| Learn value realization concepts | [Core Concepts](../core-concepts/index.md) |
| Set up SSO or invite users | [Administration](../administration/index.md) |

## The value workflow at a glance

ValuePact organizes work around a progressive workflow that moves a prospect account from raw signals to a packaged, governed business case:

1. **Accounts** — select or create a prospect account.
2. **Intelligence** — discover signals, value drivers, evidence, and stakeholders.
3. **Value Studio** — synthesize an action plan, value model, and narrative.
4. **Deliverables** — package outputs into business cases and role-specific views.
5. **Governance** — review audit trails, provenance chains, and compliance status.

Supporting these are the **Context Engine** (value packs, models, formulas, and agents) and **Settings** (tenant configuration, integrations, team, and billing).

## How this section is organized

The Getting Started section contains five pages. Each follows the same structure so you know what to expect:

| Page | What you will learn | Estimated time |
|------|---------------------|----------------|
| [What is ValuePact?](what-is-valuepact.md) | Product overview, architecture, key capabilities, and industry packs. | 5 minutes |
| [Quick Start Guide](quick-start-guide.md) | Hands-on walkthrough from sign-in to first exported report. | 20 minutes |
| [User Roles](user-roles.md) | Roles, permissions, tiered disclosure, and role-to-workspace mapping. | 10 minutes |
| [Navigating the Platform](navigating-the-platform.md) | UI anatomy: left rail, top header, workspace tabs, right rail, search. | 10 minutes |

!!! tip
    You do not need to read every page in order. Use the table above to jump to the topic that solves your immediate need.

## Platform capabilities summary

Before diving in, here is what ValuePact enables across the value workflow:

- **Intelligence gathering** — Capture signals, map value drivers, attach evidence, and identify stakeholders for every prospect account.
- **Value modeling** — Build driver trees, run formula-based ROI calculations, and generate narratives using Layer 4 agentic workflows.
- **Deliverable packaging** — Produce CFO, executive, and technical views of business cases with approval gates and export controls.
- **Governance and trust** — Review audit logs, decision traces with provenance, and health monitoring across all layers.
- **Benchmarking** — Compare your value models against curated peer datasets by industry and segment.

## Prerequisites

- [ ] A ValuePact workspace invitation or an existing Clerk-authenticated organization.
- [ ] A modern web browser (Chrome, Firefox, Edge, or Safari).
- [ ] JavaScript enabled and third-party cookies allowed for authentication.
- [ ] Screen resolution of at least 1280x720 for the full three-panel layout.

!!! note
    Mobile browsers are supported for viewing dashboards and approved deliverables. Full modeling features require a desktop viewport.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A single user can belong to a maximum of 10 organizations.

<span class="vp-badge vp-badge--limit">Limit</span> Guest access is not supported; every user must authenticate through Clerk.

<span class="vp-badge vp-badge--limit">Limit</span> Self-service sign-up is disabled by default; new users must be invited by an Admin.

## Getting help while onboarding

If you prefer guided assistance over self-service documentation:

- **In-app chat** — Use the agent stream in the **Intelligence** workspace to ask natural-language questions about platform features.
- **Support portal** — Access the [Support](../support/index.md) section for KB articles, ticket templates, and severity matrices.
- **Training** — Visit the [Training](../training/index.md) section for beginner, intermediate, and advanced learning paths.
- **Best practices** — Review [Best Practices](../best-practices/index.md) for stakeholder engagement, reporting cadence, and governance.

## Troubleshooting

??? question "Issue: I cannot find the documentation section I need"
    **Cause:** The site uses MkDocs Material navigation tabs and sections.
    **Resolution:** Use the **Search** bar in the top header, or open the **Getting Started** tab and expand sections in the left sidebar.

??? question "Issue: Links to Core Concepts return a 404"
    **Cause:** The relative path may be wrong if the page is moved.
    **Resolution:** Navigate from the top-level **Core Concepts** section in the navigation tabs. Report broken links to the docs team.

??? question "Issue: I do not know which role to assign a new team member"
    **Cause:** Role selection depends on what the user needs to do, not their title.
    **Resolution:** Use the decision matrix on [User Roles](user-roles.md). A safe default is **User** for anyone who will build value models, and **Viewer** for stakeholders who only need read access.

## Related pages

- [What is ValuePact?](what-is-valuepact.md)
- [Quick Start Guide](quick-start-guide.md)
- [User Roles](user-roles.md)
- [Navigating the Platform](navigating-the-platform.md)
- [Core Concepts](../core-concepts/index.md)

## Escalation path

If you cannot access the documentation or find a discrepancy:

1. Contact your ValuePact admin to verify organization membership and role assignment.
2. Open a support ticket with severity **S4** through the [Support](../support/index.md) portal.
3. For documentation bugs, mention `owner: docs-team` in the ticket subject.
4. For onboarding workflow issues, include the step number and the workspace name where you are stuck.
