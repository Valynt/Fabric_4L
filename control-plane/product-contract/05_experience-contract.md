# 05 — Experience Contract

Source: Master Product Intent §5 (S1). State dimensions referenced here are defined in `03_domain-lifecycle.md`.

## Persistent account workspace (shell rules)

1. Always show tenant and account/opportunity identity, reporting currency, value period, case ID, model version, selected scenario, lifecycle status, and source freshness.
2. Always show journey progress, unresolved blockers, evidence coverage, and the permitted Save, Review, Approve, Publish, and Export actions.
3. Preserve account, case, selected scenario, active tab, unsaved edits, and last successfully rendered version across navigation and refresh.
4. Treat the AI rail as context-aware assistance, not the system of record. Every proposed material change supports Accept, Edit, and Reject (R-3).
5. Do not use an action label that overstates behavior: **Generate** creates data, **Promote** persists a domain artifact, **Convert** creates the promised tree or model, **Publish** creates an immutable customer-facing version.

## Required state behavior

| State | Requirement |
|---|---|
| Loading | Keep shell and account context visible; accessible placeholders; never flash false zero values or a misleading empty state |
| Empty | Explain the missing prerequisite; provide one primary action that can actually resolve it |
| Generating | Keep last good version visible; identify active phase; prevent duplicates; allow navigation without losing the job |
| Degraded | Name the failed source/service, fallback or default used, affected outputs, publication impact. Material degradation blocks publication |
| Stale | Identify changed inputs and affected downstream artifacts; require recalculation or re-review; do not silently retain approval on a changed draft |
| Denied or expired | Render no protected account data; distinguish authentication, permission, tenant/account mismatch, expiration while preserving the attempted route |
| Conflict | Preserve local edits; offer Compare, Reload, or Save as New Version; never silently overwrite concurrent work |
| Error | Scope the failure; preserve unaffected work; provide actionable recovery; show a trace identifier |

## Review and approval gates

Review is performed against an immutable snapshot of inputs, assumptions, formulas, units, ranges, evidence and claim references, financial results, narrative, model version, source freshness, and authorization scope.

1. A reviewer can approve, request changes with anchored comments, or reject according to verified permission.
2. Approval records actor, role, timestamp, version, content hash, and rationale.
3. Editing an approved version creates a new draft and does not mutate the reviewed artifact (R-7).
4. Publish and export remain disabled until the exact version is approved, authorization is verified, required evidence passes, financial claims are traceable, and no material stale or degraded state remains.
5. The UI presents readiness as an actionable gate checklist with direct navigation to each blocker.

## Provenance presentation

- Required lineage chain: **Claim -> calculation -> formula -> assumptions -> driver -> signal or evidence -> original source** (R-8).
- Each material item shows source class, owner, date, freshness, confidence, validation status, units, time basis, and applicability.
- Source classes: **customer-provided, observed, benchmark, derived, AI-suggested, default**.
- Unverified claims and defaults remain visible in every view and export (R-1, R-5).

## Accessibility and responsive behavior (WCAG 2.2 AA)

1. Meet WCAG 2.2 AA: keyboard-complete interaction, semantic landmarks, predictable focus, text alternatives, sufficient contrast, reduced-motion support, announced operation status.
2. Never communicate lifecycle, confidence, errors, or evidence status by color alone.
3. Charts include textual summaries and accessible data-table alternatives.
4. Desktop: account shell + primary workspace + collapsible assistance/provenance rail. Tablet: collapses secondary navigation without hiding blockers. Mobile: single-column journey with persistent account context.
5. Destructive, approval, publication, export, and tenant-switch actions require explicit confirmation that states the account and version scope.
