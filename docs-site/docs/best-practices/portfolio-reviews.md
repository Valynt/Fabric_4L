---
owner: docs-team
status: active
last_reviewed: 2026-06-07
---

# Portfolio Reviews

## Overview

Portfolio reviews are the forum where leaders decide which initiatives to fund, accelerate, pause, or stop. This page provides a structure for effective reviews and clear decision frameworks.

## Who this is for

- <span class="vp-badge vp-badge--role">Executive</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">End User</span>

## Prerequisites

- Portfolio dashboard populated with active initiatives.
- Pre-agreed scoring criteria.
- Calendar invite for the review meeting with required attendees.

## Step-by-step instructions

### 1. Prepare the review pack

1. One week before the meeting, export the **Portfolio Dashboard**.
2. Include: initiative list, health scores, cumulative value, and resource consumption.
3. Distribute the pack with a pre-read request.

### 2. Run the review meeting

1. **Opening (5 min):** Remind attendees of the strategic priorities.
2. **Health check (20 min):** Review amber and red initiatives. Owners explain recovery plans.
3. **Value deep dive (20 min):** Examine top three value contributors and bottom three underperformers.
4. **Re-prioritization (10 min):** Apply the decision framework.
5. **Actions (5 min):** Assign owners and deadlines for every decision.

### 3. Apply a decision framework

Use the RICE scoring model adapted for value management:

| Factor | Question | Score |
|--------|----------|-------|
| Reach | How many stakeholders benefit? | 1–10 |
| Impact | What is the expected financial or strategic value? | 1–10 |
| Confidence | How certain is the evidence? | 1–10 |
| Effort | What is the remaining cost and timeline? | 1–10 (inverse) |

Sort initiatives by `(Reach × Impact × Confidence) / Effort`. Fund the top until budget is consumed.

### 4. Document decisions

1. For every initiative, record the decision: **Continue**, **Accelerate**, **Pause**, or **Stop**.
2. Update the initiative status in ValuePact immediately.
3. Add a comment explaining the rationale for audit purposes.

### 5. Communicate outcomes

1. Send a summary email within 24 hours.
2. Update the **Portfolio Dashboard** filters to reflect new priorities.
3. Schedule follow-up checkpoints for paused or stopped initiatives.

## Permissions required

| Role | Permission | Scope |
|------|-----------|-------|
| Executive | Update portfolio status | Organization |
| Admin | Configure portfolio views | Organization |
| User | Update initiative status | Own initiatives |

## Limits and guardrails

- <span class="vp-badge vp-badge--limit">Limit</span> Initiatives per portfolio review: 30.
- <span class="vp-badge vp-badge--limit">Limit</span> Custom scoring fields: 10.
- <span class="vp-badge vp-badge--limit">Limit</span> Decision comments: 2,000 characters.

## Troubleshooting

??? question "Issue: Reviews become status updates with no decisions"
    **Cause:** The forum lacks a clear decision framework, or attendees are not empowered to reallocate resources.
    **Resolution:**
    1. Pre-circulate the scoring model.
    2. Require finance or the value office to attend.
    3. Time-box each section and enforce it.

??? question "Issue: Stopped initiatives restart without approval"
    **Cause:** There is no gate preventing reactivation.
    **Resolution:**
    1. Add a workflow rule requiring executive approval to move from **Stopped** to **Draft**.
    2. Monitor audit logs for unauthorized reactivations.

## Related pages

- [Reporting Cadence](reporting-cadence.md)
- [Executive Adoption](executive-adoption.md)
- [Governance](governance.md)

## Escalation path

| Severity | Condition | Contact |
|----------|-----------|---------|
| General | Portfolio review facilitation | Customer Success Manager |
| Urgent | Dispute over scoring or re-prioritization | support@valuepact.ai |
