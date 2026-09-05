# SPEC_GAPS.md — GATE-1 (blocking)

**Pipeline:** `autonomous-completion-final-20` v2.0.0
**Repo:** Valynt/Fabric_4L
**Anchor SHA:** `4bb4e142c2ccbc56297de843e71534d956bb198f` (main, Value Studio Slice 1 #1679)
**Generated:** 2026-09-05T15:20:00Z
**Rule:** agents_must_not_guess_product_intent
**Status:** `spec_gaps_signed_off == false` — waiting on human review

This file lists items where completing the remaining ~20% requires a human
decision. Nothing below is an implementation plan. Options are recorded only
so the signer can pick; they are not recommendations.

---

## Halt already in effect (not a product-intent question)

**GAP-0 — Existing suite is red on the 80%.**

- Evidence: [PR Checks #33970450342](https://github.com/Valynt/Fabric_4L/actions/runs/33970450342) failed (`02-code-quality-and-tests`, Docker/e2e/runtime-contract, unified readiness). [Prod Readiness Gates #33970450317](https://github.com/Valynt/Fabric_4L/actions/runs/33970450317) failed (`prod-readiness`, `release-policy`, `gate-engineering`, `dependency-chaos`, `readiness-10`). Certify RC and Build and Deploy also failed. Critical Gates / Security / Contract / Supply Chain / Zero Trust passed on the same SHA.
- Pipeline action taken: **do not start steps 2–6**. Step 1 mapping is the only continuation.
- Decision needed: classify unclassified red jobs (especially `02-code-quality-and-tests` and prod-readiness) as (a) blocking until green, (b) known environment-dependent accepted risk, or (c) waived with owner signature.

---

## Product / slice sequencing

### GAP-1 — Value Studio Slice 2+ scope and order

Contract `docs/contracts/FE-VOS-STUDIO-001.md` lists deliberately unresolved items. Slice 1 is fixture-only; domain actions print `COMMAND_BACKEND_NOTICE`.

| Open item (from contract, not inferred) | Named owner in contract |
| --- | --- |
| Backend projection adapter behind existing seam | Platform/backend |
| Mission command channel (accept/edit/defer/pause/resume/undo) | Mission backend |
| Activity event streaming (`latestEventCursor`) | Mission backend |
| Deterministic calculation service integration | Calc service |
| Generative lens rendering | Product/platform (Thesys/OpenUI evaluated and **not adopted**) |
| Publication workflow beyond blocked/provisional display | Governance |
| Rewind/undo of activity events | Mission backend |

**Intent required:** which of these are in the “final 20%”, in what order, and what is out of Core GA.

### GAP-2 — Q3/Q4 roadmap vs remaining 20%

Root `ROADMAP.md` Q3/Q4 items (real-time collaboration, mobile, CRM webhooks, analytics dashboards, custom formula builder, value-realization tracking) are product schedule, not tickets. **Do not treat them as DAG nodes unless signed in.**

### GAP-3 — RFC-001 Formula Scenario endpoint

`contracts/rfcs/RFC-001-formula-scenario-endpoint.md` is marked **Approved** (2026-04-27) for `POST /api/v1/formulas/scenario`. Implementation status was not assumed. **Intent required:** still wanted as-specified, superseded, or already shipped under another path.

### GAP-4 — RFC-002 journey-id on L4 agent stream

File exists under `contracts/rfcs/`. **Intent required:** approve for DAG, defer, or close as already implemented.

### GAP-5 — Open GitHub contract RFCs (council)

| Issue | Title |
| --- | --- |
| [#1675](https://github.com/Valynt/Fabric_4L/issues/1675) | L4 Agent Runtime `/v1/runtime/*` + agent-runtime JSON schemas |
| [#1636](https://github.com/Valynt/Fabric_4L/issues/1636) | Event payload schemas, tool/prompt/skill registries, `x-tenant-scope` |
| [#1613](https://github.com/Valynt/Fabric_4L/issues/1613) | Consolidate billing ownership in Layer 4 |

COMPAT-L4-003 is already archived: L4 billing is currently the canonical runtime. RFC-1613 may be obsolete or may reverse that. **Council must say which.**

---

## Security / tenancy (intent: ship now vs later)

### GAP-6 — Slice T MEDIUM: `Neo4jVariableRegistry` unscoped

PR [#1684](https://github.com/Valynt/Fabric_4L/pull/1684) is docs-only. Finding: L4 `Neo4jVariableRegistry` performs CRUD/search with no tenant scoping. 31 other graph/vector surfaces were SAFE.

**Intent required:** treat as a DAG node in this pipeline, a separate security PR, or accepted residual risk.

### GAP-7 — Document-export tenant ownership

Open PR [#1669](https://github.com/Valynt/Fabric_4L/pull/1669). **Intent required:** in-scope for this pipeline or leave to that PR.

### GAP-8 — L5 `claim.approve` multi-model authorization

Open PR [#1650](https://github.com/Valynt/Fabric_4L/pull/1650). **Intent required:** in-scope or independent.

---

## Toolchain / supply chain (do not silently “fix”)

### GAP-9 — pnpm 10.18.1 pin vs P0 #1639 `>=10.34.5`

AGENTS.md and `.tool-versions` pin `pnpm 10.18.1`. Issue [#1639](https://github.com/Valynt/Fabric_4L/issues/1639) and PR [#1645](https://github.com/Valynt/Fabric_4L/pull/1645) demand a security upgrade. Changing the pin is a policy decision with lockfile blast radius (#1643, #1644).

### GAP-10 — Python 3.11.15 vs 3.11.10

`.python-version` = `3.11.15`; `.tool-versions` = `python 3.11.10`. **Intent required:** which is canonical.

### GAP-11 — `apps/web/pnpm-lock.yaml` vs root-lockfile policy

AGENTS.md: “do not introduce package-local lockfiles”. `apps/web/pnpm-lock.yaml` exists (499808 bytes) alongside root `pnpm-lock.yaml`. **Intent required:** delete, ignore, or amend the policy.

---

## Compatibility debt past target dates

### GAP-12 — Overdue CDR rows (target 2026-08-31, today 2026-09-05)

From `docs/governance/compatibility-debt-registry.md` (active, not struck):

- COMPAT-L1-001
- COMPAT-L3-001, COMPAT-L3-002, COMPAT-L3-005
- COMPAT-WEB-004, COMPAT-WEB-018, COMPAT-WEB-019, COMPAT-WEB-020
- COMPAT-L4-001, COMPAT-L4-004

**Intent required per row:** extend dated target, remove shim now, or keep until a named consumer migrates.

### GAP-13 — Skills path promotion (#1683) vs FAB-106

PR [#1683](https://github.com/Valynt/Fabric_4L/pull/1683) promotes `.agent/skills` → `agents/skills` with COMPAT-SKILLS-001 (removal 2026-12-31). Merge-order note vs FAB-106 is recorded on the PR. **Intent required:** land S now, wait for FAB-106, or drop.

---

## Test-debt tickets (skip vs implement)

### GAP-14 — L1 idempotency / terminal / robots

Mixed `TODO(...)` and `DONE(...)` skips:

- `TODO(VF-L1-IDEMPOTENCY-DEBT-001)` format validation **not implemented**
- several sibling idempotency items marked DONE with “unit test still pending”
- `TODO(VF-L1-TERMINAL-DEBT-001)` stuck-jobs loop not wired to metrics; backoff item marked DONE with test pending
- `DONE(VF-L1-ROBOTS-DEBT-001)` tests still skipped

**Intent required:** close DONE skips with tests, implement remaining TODOs, or keep as known skips.

### GAP-15 — L4 skipped suites (issue #1593)

- VF-L4-AUTH-DEBT-001 (5 skips) — “API authentication middleware requires additional setup”
- VF-L4-AUDIT-DEBT-001 (2 skips)
- DEFERRED permission-system contract (4 skips in `test_analysis_smoke_mode_service_routes.py`)
- DEFERRED usage-idempotency / async-session / pydantic `event_count` type (4 skips)

**Intent required:** these are test-infra vs real product-behavior holes. Do not let an agent “make them pass” by editing tests after step 3 freeze.

### GAP-16 — L3 Neo4j session lifecycle

`TODO(lifecycle)` in `services/layer3-knowledge/src/api/dependencies_tenant_secured.py:336`. PR [#1661](https://github.com/Valynt/Fabric_4L/pull/1661) already targets per-request cleanup. **Intent required:** this pipeline owns it, or #1661 does.

---

## Ops items still `requires implementation` in the audit register

### GAP-17 — S5-2 / S5-3 / S5-4

From `docs/governance/audit-remediation-sprint-register.md` (status `requires implementation`):

- S5-2 ArgoCD install + sync evidence
- S5-3 WAL-G placeholders + restore drill
- S5-4 OpenTelemetry tracing migration (live trace receipt)

These need environment and owner, not code guesses.

### GAP-18 — Launch P0/P1 environment evidence

`docs/readiness/current.md` is **BLOCKED**. `docs/launch/launch-blocker-register.md` still requires staging evidence for P0-001 (4 of 7 journeys), rollback drill, SSO (scoped out of Core GA), billing provider, live LLM, alert receivers.

**Intent required:** is “final 20%” Core-GA waiver, paid-GA, or repository-owned code only?

### GAP-19 — SDK `vf auth login` loopback

`TODO(VF-SDK-AUTH-DEBT-001)` on main; replacement PR [#1681](https://github.com/Valynt/Fabric_4L/pull/1681) exists (and ballooned #1624 should be closed). **Intent required:** merge #1681 outside this pipeline or include it.

---

## Sign-off

Reply with:

1. **GAP-0 classification** (block / accepted-risk / waive)
2. **In-scope IDs** for the final-20% DAG (subset of GAP-1–19)
3. **Out-of-scope IDs** (explicit)
4. **Owner + max budget** (LOC/files) per in-scope item, or “use pipeline defaults”

Until this file is signed, `spec_gaps_signed_off` remains false and step_2 is not started.
