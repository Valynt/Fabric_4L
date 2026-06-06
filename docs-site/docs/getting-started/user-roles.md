---
owner: docs-team
status: draft
last_reviewed: 2026-06-06
---

# User Roles

ValuePact uses two complementary mechanisms to control what a user sees and can do:
**experience tiers** and **roles**.

## Purpose

Explain the tiers and roles that determine access and capability.

## Audience

- Admin
- Executive
- End user

## Experience tiers

The interface progressively discloses capability by tier:

- **Standard** — simplified flows for business users.
- **Advanced** — power-user modeling and inspection tools.
- **Admin** — governance controls and tenant configuration.

Users can switch between Standard and Advanced; Admin capabilities are gated.

## Roles

Access to administrative surfaces is governed by roles, including:

- **Super Admin** and **Tenant Admin** — full administration, billing, team, and governance.
- **Content Admin** — governance and content configuration.
- **Analyst** — works within the value workflow.
- **Editor** — may view team membership and selected data surfaces.
- **Read Only / Viewer** — inspect membership, roles, and policy matrices without mutating.

## Examples of role-gated areas

- **Account & Billing** — Tenant Admins and Super Admins; standard users do not see payment methods.
- **Team & Access** — Admins manage members, roles, permissions, and API keys.
- **Governance** — restricted to Tenant Admins, Content Admins, and Super Admins; audit trail is
  read-only for most admins.

## Related pages

- [Navigating the Platform](navigating-the-platform.md)
- [Administration](../administration/index.md)
