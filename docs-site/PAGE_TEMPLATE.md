# Page Template Standard

Every user-facing documentation page must follow this structure.

## Front matter

```yaml
---
owner: docs-team
status: active
last_reviewed: YYYY-MM-DD
---
```

Status values: `draft` | `active` | `deprecated`

## Required sections

### 1. Page title (H1)
Clear, action-oriented or noun-phrase title.

### 2. Overview (2-4 sentences)
What this page covers and why the reader should care. No internal jargon without definition.

### 3. Who this is for
Use role badges:
- <span class="vp-badge vp-badge--role">End User</span>
- <span class="vp-badge vp-badge--role">Admin</span>
- <span class="vp-badge vp-badge--role">Executive</span>
- <span class="vp-badge vp-badge--role">Developer</span>

### 4. Prerequisites
What the reader needs before starting (access, data, config, other pages read).

### 5. Step-by-step instructions
Numbered steps. Each step is one action. Include UI path references (`**Bold**` for buttons/labels, `Code` for fields/values). Use admonitions for warnings and tips.

### 6. Permissions required
Table of who can do what:

| Role | Permission | Scope |
|------|-----------|-------|
| Admin | Configure | Organization |
| User | View | Assigned initiatives |

Use <span class="vp-badge vp-badge--permission">Required</span> badges.

### 7. Limits and guardrails
Rate limits, max counts, validation rules, timeouts. Use <span class="vp-badge vp-badge--limit">Limit</span> badges.

### 8. Troubleshooting
Common issues and resolutions in a details/summary block:

```markdown
??? question "Issue: symptom"
    **Cause:** explanation
    **Resolution:** steps
```

### 9. Related pages
Bulleted list with relative links to next/previous logical pages.

### 10. Escalation path
Who to contact if the issue persists (support tier, Slack channel, ticket severity).

## Writing rules

- Use second person ("you").
- Keep sentences under 25 words.
- One idea per paragraph.
- Define acronyms on first use.
- Use active voice.
- No placeholder text ("Explain what this page helps", "What belongs here").
- No "screenshot coming soon" — use ASCII diagrams, tables, or code blocks instead.
- Cross-link generously.
- Every claim must be verifiable from the codebase or contracts.
