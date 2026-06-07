---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Navigating the Platform

ValuePact uses a three-layer navigation model: a global left rail, horizontal workspace tabs, and a contextual right rail. Understanding this model helps you move quickly between accounts, intelligence, modeling, and governance without losing context.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Overview

The UI is organized around a persistent **left rail** that lists the seven primary domains. Selecting a domain loads a **workspace** with horizontal tabs. Many workspaces include a **right rail** that shows detail panels, agent streams, or contextual actions. A fixed **top header** provides search, notifications, and the active mode indicator.

## Left rail: global navigation

The left rail is a single stable spine that grows with your tier. It contains seven domains:

| # | Domain | Icon | Purpose |
|---|--------|------|---------|
| 1 | **Accounts** | Building2 | Select or create a prospect account. |
| 2 | **Intelligence** | Radar | Discovery workspace: Signals, Drivers, Evidence, Stakeholders. |
| 3 | **Value Studio** | Lightbulb | Synthesis workspace: Action Plan, Value Model, Narrative. |
| 4 | **Context Engine** | Wrench | Value packs, models, formulas, and agents. |
| 5 | **Deliverables** | FileText | Packaged outputs for sharing. |
| 6 | **Governance** | GitBranch | Audit, provenance, and compliance. |
| 7 | **Settings** | Settings | Tenant configuration and administration. |

!!! tip
    Click the **Collapse navigation** button at the top of the left rail to shrink it to icon-only mode. Click again to expand.

### Tiered disclosure

The left rail hides Advanced and Admin items from users in **Standard** mode. Eligible users can switch tiers using the **Tier Switcher** in the rail footer:

- **Standard Mode** — simplified flows for business users.
- **Advanced Mode** — exposes power-user modeling, formula editing, and inspection tools.
- **Admin Mode** — visible only to **Admin** and **Super Admin** roles; shows governance and configuration.

## Top header

The fixed header at the top of the screen contains:

- **Platform name and tagline** — click to return to the **Command Center**.
- **Global Search** — press `⌘K` or click the search pill to search across accounts, signals, stakeholders, and business cases.
- **Mode pill** — displays your current tier (**Standard**, **Advanced**, or **Admin**).
- **Notifications** — bell icon with unread count.
- **User avatar** — opens a dropdown with **Profile**, **Notifications**, **Preferences**, and **Log out**.

!!! note
    The header is sticky and remains visible while you scroll through long workspaces.

## Workspace tabs

After selecting a domain from the left rail, the main content area shows horizontal tabs specific to that workspace:

### Intelligence tabs

- **Signals** — pain signals and opportunities with confidence scores.
- **Drivers** — weighted value drivers and driver trees.
- **Evidence** — supporting claims with source attribution.
- **Stakeholders** — mapped contacts with roles and influence levels.

### Value Studio tabs

- **Action Plan** — prioritized initiatives with timelines and owners.
- **Value Model** — variables, formulas, and ROI calculations.
- **Narrative** — auto-generated executive summary and value proposition.

### Deliverables tabs

- **Business Cases** — list of cases with status badges (**draft**, **approved**).
- **Exports** — previously generated PDFs and shared links.

### Governance tabs

- **Audit Log** — tenant-scoped action history.
- **Traces** — decision provenance chains.
- **Health** — system component status dashboard.

## Right rail: contextual panel

The right rail provides contextual support for the current screen. It is sticky on desktop and collapses into a drawer on mobile.

| Workspace | Right Rail Content |
|-----------|-------------------|
| **Intelligence** | **Agent Chat** — ask questions, synthesize signals, request summaries. |
| **Value Studio** | **Variable Inspector** — edit inputs and see live recalculation. |
| **Deliverables** | **Export Actions** — select format (CFO, Executive, Technical view). |
| **Governance** | **Trace Detail** — provenance chain for a selected decision. |

!!! tip
    Close the right rail to expand the main workspace. Click the **Close panel** button in the rail header.

## Drilldowns and detail views

ValuePact uses three patterns for drilling into details:

1. **Right rail panel** — the default for signals, stakeholders, and trace details.
2. **Overlay drawers** — used for account creation, variable editing, and integration configuration.
3. **Full-page views** — used for business case review, dashboard analytics, and audit log filtering.

## Status indicators

Status appears as colored badges and icons throughout the platform:

| Status | Color | Meaning |
|--------|-------|---------|
| **approved** | Green | Reviewed and cleared for export. |
| **draft** | Gray | In progress; export blocked. |
| **ready** | Blue | Data loaded and available for review. |
| **low-confidence** | Amber | Signal or claim below the confidence threshold. |
| **degraded** | Red | System component experiencing issues. |
| **healthy** | Green | All systems operational. |

## Search

The **Global Search** dialog (`⌘K`) searches across:

- Prospect accounts by name or industry.
- Signals by title or source.
- Stakeholders by name or role.
- Business cases by title.

Results are scoped to your current tenant. Cross-tenant results never appear.

## Organization switcher

Users who belong to multiple Clerk organizations can switch contexts:

1. Click your **avatar** in the top header.
2. Select **Switch Organization** (if enabled by your admin).
3. Choose a different workspace from the list.

!!! warning
    Switching organizations reloads the page and resets the active account selection. Save any in-progress work before switching.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure branding and navigation | Organization |
| User | Use search and right rail | Organization |
| Viewer | View search results (read-only) | Assigned accounts |

<span class="vp-badge vp-badge--permission">Required</span> The **Admin** tier in the left rail is only visible to **Admin** and **Super Admin** roles.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> The right rail panel has a maximum width of 480px on desktop.

<span class="vp-badge vp-badge--limit">Limit</span> Global search returns a maximum of 20 results per category.

<span class="vp-badge vp-badge--limit">Limit</span> Mobile devices below the `md` breakpoint show a persistent mobile sidebar instead of the desktop left rail.

## Troubleshooting

??? question "Issue: The left rail is missing domains I expect to see"
    **Cause:** Your tier is set to **Standard**, or your role does not grant access to the domain.
    **Resolution:** Open the **Tier Switcher** in the left rail footer and enable **Advanced Mode** if available. If the domain is **Settings** or **Governance**, ask an admin to verify your role.

??? question "Issue: The right rail is blank or shows a loading skeleton"
    **Cause:** The panel data is still loading, or the selected item has no contextual data.
    **Resolution:** Wait for the loading state to resolve. If it persists, try selecting a different item in the main workspace. For the agent chat, ensure the account is selected and the agent runtime is healthy.

??? question "Issue: Search returns no results for an account I know exists"
    **Cause:** The account belongs to a different organization, or your role restricts account visibility.
    **Resolution:** Verify you are in the correct organization. If using the organization switcher, select the organization that owns the account. Admins can check account assignments in **Settings**.

??? question "Issue: Workspace tabs do not respond to clicks"
    **Cause:** The state machine transition is invalid (for example, missing account context).
    **Resolution:** Ensure a prospect account is selected in **Accounts**. Some tabs are disabled until an account is active.

## Related pages

- [Quick Start Guide](quick-start-guide.md)
- [User Roles](user-roles.md)
- [What is ValuePact?](what-is-valuepact.md)
- [Core Concepts: Initiatives](../core-concepts/initiatives.md)
- [Core Concepts: Business Cases](../core-concepts/business-cases.md)
- [Core Concepts: Stakeholders](../core-concepts/stakeholders.md)

## Escalation path

If navigation or UI rendering issues persist:

1. Refresh the browser and verify your tier and role.
2. Check **Governance** > **Health** for frontend or API degradation.
3. Review [Troubleshooting: Missing Data](../troubleshooting/missing-data.md).
4. Open a support ticket with severity **S4** and include your browser version, URL, and a description of the missing or broken element.
