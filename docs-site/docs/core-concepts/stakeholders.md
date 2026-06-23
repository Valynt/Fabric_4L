---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Stakeholders

Stakeholders are the people and roles mapped during discovery who influence, approve, or benefit from a value initiative. Accurate stakeholder mapping ensures messaging is personalized and decisions are aligned.

## Who this is for

<span class="vp-badge vp-badge--role">End User</span>
<span class="vp-badge vp-badge--role">Admin</span>
<span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- A ValuePact account created in the system
- Access to the **Intelligence** workspace
- Optionally, CRM integration (Salesforce or HubSpot) for automatic contact sync

## Overview

Stakeholder records include name, title, department, persona, influence level, and decision role. They are linked to [value hypotheses](opportunities.md) and [business cases](business-cases.md) so that narratives can be tailored by audience.

## Stakeholder roles

| Role | Description | Typical concerns |
|------|-------------|-----------------|
| Economic buyer | Controls budget and signs contracts | ROI, payback, risk |
| Champion | Internal advocate for the solution | Outcomes, feasibility, timeline |
| Evaluator | Assesses technical or operational fit | Capabilities, integration, roadmap |
| Compliance/Legal | Reviews regulatory and legal requirements | Risk, auditability, data handling |
| Operational user | Uses the solution day-to-day | Ease of use, training, support |

### Persona mapping

Each stakeholder is linked to a persona from your value pack ontology. Personas define:

- **Priorities** — top strategic objectives for this role
- **Pains** — common friction points experienced
- **Messaging themes** — value narratives proven to resonate
- **Preferred proof points** — benchmarks, case studies, or analyst reports

When generating a business case, the platform selects messaging themes and proof points based on the persona of the intended audience. A CFO receives financial narratives with benchmark data. A technical evaluator receives capability mappings with integration roadmaps.

## Mapping stakeholders

### Automatic enrichment

If CRM integration is enabled, ValuePact pulls contacts from the account's opportunity and enriches them with LinkedIn data. The platform infers decision roles based on title patterns.

### Manual entry

1. Open the account's **Intelligence** workspace.
2. Click the **Stakeholders** tab.
3. Click **Add Stakeholder**.
4. Enter name, title, and email.
5. Select a persona from the value pack ontology.
6. Set influence level: **High**, **Medium**, or **Low**.
7. Set decision role: **Economic buyer**, **Champion**, **Evaluator**, **Compliance**, or **Operational user**.
8. Click **Save**.

### Bulk import

Upload a CSV with columns: `name`, `title`, `email`, `department`, `persona_id`, `influence_level`, `decision_role`. The system validates persona IDs against the account's value pack.

## Engagement tracking

Stakeholder engagement is tracked across touchpoints:

- **Business case views** — which stakeholders opened which deliverable view
- **Meeting notes** — linked to stakeholder records
- **Feedback** — validation notes from hypothesis reviews
- **Sentiment** — inferred from email tone or meeting transcripts (if enabled)

### Influence matrix

The influence matrix visualizes stakeholders by decision role and influence level:

| | High influence | Medium influence | Low influence |
|---|---------------|------------------|---------------|
| **Economic buyer** | Primary approver | Secondary approver | Inform only |
| **Champion** | Mobilizes support | Provides references | Passive advocate |
| **Evaluator** | Gatekeeper | Technical advisor | End user |
| **Compliance** | Regulatory blocker | Policy reviewer | Not involved |

Use the matrix to identify gaps. An initiative with no high-influence champion is flagged as "at risk" in stakeholder health.

## RACI mapping

For complex initiatives, stakeholders can be assigned RACI roles per project task:

| RACI | Meaning |
|------|---------|
| Responsible | Does the work |
| Accountable | Owns the outcome |
| Consulted | Provides input |
| Informed | Kept up to date |

To configure RACI, open the initiative's **Stakeholders** panel, select a stakeholder, and toggle RACI assignments for each milestone.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure persona ontologies | Organization |
| User | Add and edit stakeholders | Assigned accounts |
| User | View engagement history | Assigned accounts |
| Executive | View stakeholder maps across initiatives | Organization |

<span class="vp-badge vp-badge--permission">Required</span> `stakeholders:write` to add or edit; `stakeholders:read` to view.

## Limits and guardrails

<span class="vp-badge vp-badge--limit">Limit</span> A maximum of 100 stakeholders per account.

<span class="vp-badge vp-badge--limit">Limit</span> CRM sync runs every 4 hours. Manual sync is available once per hour.

<span class="vp-badge vp-badge--limit">Limit</span> Engagement sentiment analysis is available only when the Microsoft Teams or Slack integration is enabled.

## Troubleshooting

??? question "Issue: CRM sync creates duplicate stakeholders"
    **Cause:** The same contact exists in multiple CRM objects (lead, contact, opportunity contact role).
    **Resolution:** In **Settings > Integrations > CRM**, enable **Deduplicate by email** and run a manual resync.

??? question "Issue: Stakeholder persona is not available in the dropdown"
    **Cause:** The account's value pack does not include the requested persona, or the value pack is outdated.
    **Resolution:** Contact an admin to update the value pack ontology in **Administration > Value Packs**.

??? question "Issue: Engagement tracking shows no data for a stakeholder"
    **Cause:** The stakeholder has not been linked to a delivered business case, or email tracking is disabled.
    **Resolution:** Confirm the stakeholder is added to the account and that **Email Tracking** is enabled in workspace settings.

??? question "Issue: Influence matrix shows a missing champion for an account"
    **Cause:** No stakeholder is tagged with the Champion role, or the champion was accidentally archived.
    **Resolution:** Review the stakeholder list and add or restore a champion. Accounts without champions are flagged in pipeline reviews.

## Related pages

- [Opportunities](opportunities.md)
- [Business Cases](business-cases.md)
- [Initiatives](initiatives.md)
- [Projects](projects.md)

## Escalation path

For CRM sync or integration issues, contact your admin or integration owner. For ontology or persona gaps, escalate to Value Engineering via Slack `#value-packs`.

### Stakeholder import template

A sample CSV header for bulk import:

```csv
name,title,email,department,persona_id,influence_level,decision_role
Alice Chen,CFO,alice@example.com,Finance,cfo_v1,High,economic_buyer
Bob Smith,VP Engineering,bob@example.com,Engineering,vpe_v1,Medium,evaluator
```

`persona_id` must match an entry in the account's value pack ontology.