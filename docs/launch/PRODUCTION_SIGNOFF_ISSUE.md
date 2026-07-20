# Production Signoff Tracking Issue (Single Source of Truth)

> **Audit note (2026-07-18):** The linked authority doc `PRODUCTION_SIGNOFF.md` does not exist at the expected location (`docs/launch/PRODUCTION_SIGNOFF.md`). An archived copy exists at `archive/signoff-evidence/signoff-evidence/PRODUCTION_SIGNOFF.md`; update this link once the canonical location is confirmed.

- **Issue title:** `Production Signoff Runway — Full Monorepo`
- **Owner:** Release Manager (assign explicitly)
- **Status:** Open
- **Decision meeting target date:** TBD
- **Linked authority doc:** `PRODUCTION_SIGNOFF.md`

## Rules

- Every production-signoff PR/task must reference this issue.
- Architecture-changing work is frozen unless approved via ADR and linked here.
- Evidence must be attached per phase before phase closure.

## Phase Checklist

- [ ] Phase 0 — Scope freeze complete
- [ ] Phase 1 — Source of truth locked
- [ ] Phase 2 — Monorepo hygiene complete
- [ ] Phase 3 — Build reproducibility complete
- [ ] Phase 4 — Contract enforcement green
- [ ] Phase 5 — Security gate green
- [ ] Phase 6 — Data/migration readiness green
- [ ] Phase 7 — Frontend readiness green
- [ ] Phase 8 — Backend readiness green
- [ ] Phase 9 — Live full-stack evidence attached
- [ ] Phase 10 — Observability/operations gate green
- [ ] Phase 11 — Performance/resilience gate green
- [ ] Phase 12 — Kubernetes/infra readiness green
- [ ] Phase 13 — Release governance complete
- [ ] Phase 14 — Final go/no-go criteria all green

## Required Evidence Attachments

- [ ] Clean clone/build/test evidence
- [ ] OpenAPI export + drift comparison evidence
- [ ] Tenant/auth/security suite evidence
- [ ] Live staging/Bunnyshell deploy evidence
- [ ] P0 Playwright live JUnit/trace/video/screenshots
- [ ] Observability dashboards + alert routing verification
- [ ] Migration + rollback validation evidence
- [ ] Release risk register + known issues + deferred decisions

## Go/No-Go Formula

`clean build + clean migrations + clean security gate + clean contract gate + clean live P0 Playwright evidence + clean observability gate + documented rollback + named owners = production candidate`
