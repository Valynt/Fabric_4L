---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Stakeholder Engagement

## Overview

Value initiatives live or die by stakeholder commitment. This page describes how to set communication cadence, manage expectations, and build feedback loops that sustain momentum.

## Who this is for

- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Executive</span>

## Prerequisites

- Initiative owner role in ValuePact.
- Stakeholder list with roles and influence levels.
- Communication tools configured (email, Slack, or Teams).

## Step-by-step instructions

### 1. Map stakeholders

1. Open the initiative and select the **Stakeholders** tab.
2. Add each stakeholder with their role: **Sponsor**, **Owner**, **Contributor**, or **Viewer**.
3. Tag influence level: **High**, **Medium**, or **Low**.
4. Note communication preferences in the description field.

### 2. Set a communication cadence

| Stakeholder Type | Cadence | Channel | Content |
|------------------|---------|---------|---------|
| Sponsor | Weekly | Slack DM or email | Status, risks, decisions needed |
| Owner | Daily | In-app comment or Slack | Blockers, actuals, next steps |
| Contributor | Weekly | Teams channel or email | Task assignments, deadlines |
| Viewer | Monthly | Email digest | Summary metrics, milestones |

### 3. Define expectation gates

1. At kickoff, document what success looks like at 30, 60, and 90 days.
2. Share the document via the initiative **Files** tab.
3. Reference the gates in every status update to maintain accountability.

### 4. Build feedback loops

1. After each milestone, send a 3-question pulse survey.
2. Questions: What worked? What blocked you? What should change?
3. Summarize responses in the initiative **Comments** and assign action items.

### 5. Escalate early

1. Define a risk threshold (e.g., 2 weeks behind schedule or 10% over budget).
2. When the threshold is hit, notify the sponsor within 24 hours.
3. Use the **Escalate** button in the workflow to trigger the approval chain.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| User | Manage stakeholders | Own initiatives |
| User | Send notifications | Own initiatives |
| Admin | Configure notification defaults | Organization |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Stakeholders per initiative: 50.
- <span class="vp-badge vp-badge--limit">Limit</span> Custom notification rules: 10 per initiative.
- <span class="vp-badge vp-badge--limit">Limit</span> Digest frequency: daily, weekly, or monthly only.

## Troubleshooting

??? question "Issue: Stakeholders ignore updates"
    **Cause:** The channel or cadence does not match their preference, or the content is too detailed.
    **Resolution:**
    1. Switch to the stakeholder’s preferred channel.
    2. Lead with the decision needed, not the narrative.
    3. Keep updates under 5 sentences.

??? question "Issue: Feedback loops collect no responses"
    **Cause:** The survey is too long or sent at the wrong time.
    **Resolution:**
    1. Limit to one multiple-choice and one open text question.
    2. Send immediately after a milestone while context is fresh.
    3. Share aggregated results to show the loop is valued.

## Related pages

- [Executive Adoption](executive-adoption.md)
- [Reporting Cadence](reporting-cadence.md)
- [User FAQ](../faq/user-faq.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | Communication strategy | Customer Success Manager |
| Urgent | Stakeholder conflict affecting delivery | support@valuepact.ai |
