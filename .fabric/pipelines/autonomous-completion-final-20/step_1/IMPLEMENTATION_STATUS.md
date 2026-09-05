# Implementation-status evidence (GAP factual questions)

**Anchor:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**Method:** GitHub file/search + issue/PR metadata. No product intent inferred.  
**Recommendations** are labeled as such; they are not decisions.

## GAP-1 — Value Studio Slice 2+

**Evidence:** [FE-VOS-STUDIO-001.md](https://github.com/Valynt/Fabric_4L/blob/4bb4e142c2ccbc56297de843e71534d956bb198f/docs/contracts/FE-VOS-STUDIO-001.md) on main. Slice 1 merged as #1679 (anchor includes it).

Contract §2 “Deliberately unresolved (Slice 2+)” and §6 “Phase 2 — smallest safe next step”:

| Sub-id | Item | Named owner in contract | Slice 1 state |
|---|---|---|---|
| GAP-1a | Backend projection adapter behind existing `ValueStudioProjectionAdapter` seam | Platform/backend | Fixture adapter only. §6 names this as the smallest next step. |
| GAP-1b | Mission command channel (accept/edit/defer/pause/resume/undo) | Mission backend | `COMMAND_BACKEND_NOTICE` (DEC-FE-005). |
| GAP-1c | Activity event streaming (`latestEventCursor`) | Mission backend | Projected trail only. |
| GAP-1d | Deterministic calculation service integration | Calc service | Impact read-only in FE. |
| GAP-1e | Generative lens rendering | Product/platform | Thesys/OpenUI **not adopted**; `StaticGenerativeUIFallback` shipped. |
| GAP-1f | Publication workflow beyond blocked/provisional display | Governance | Labels only. |
| GAP-1g | Rewind/undo of activity events | Mission backend | Control renders only if `allowedActions` authorize. |

**Recommendation (not a choice):** if any Slice 2 work is in AC-20, start with GAP-1a only (contract §6). Do not treat 1b–1g as one node.

## GAP-2 — Q3/Q4 ROADMAP.md

Roadmap items are a product schedule, not tickets. **Recommendation:** out of AC-20 unless separately ticketed and signed.

## GAP-3 — RFC-001 Formula Scenario endpoint

**RFC file:** Approved 2026-04-27. Path `POST /api/v1/formulas/scenario`. Council note: frontend hook `useFormulaScenario` implemented Sprint 4 (commit `4978c58`).

**Search on main `4bb4e14`:**

- `contracts/openapi` path `/formulas/scenario`: **0 hits**
- L3 `formulas_evaluation_routes.py` exists; no `scenario` route match in code search
- Frontend: `apps/web/src/hooks/useFormulaScenario.ts` present

**Factual status:** contract approved; **L3 endpoint not present** in OpenAPI or route search; FE hook exists. Not “already shipped.”

**Recommendation:** implement as specified **or** supersede/close the RFC. Agents must not pick.

## GAP-4 — RFC-002 journey_id

**In-tree RFC-002** still says “Pending Council Review.”

**GitHub evidence (overrides the stale header):**

- Implementation PR [#1385](https://github.com/Valynt/Fabric_4L/pull/1385) **merged** 2026-08-21 (`journey_id` on `AgentStreamRequest` / `AgentGovernanceMetadata`; `_resolve_journey_id` in `conversation.py`).
- RFC markdown PR [#1543](https://github.com/Valynt/Fabric_4L/pull/1543) **merged**.
- Tracking issue [#1387](https://github.com/Valynt/Fabric_4L/issues/1387) **closed completed** 2026-08-28 by `valyntxyz`.
- Code search: `journey_id` present in `agent_stream.py`, `conversation.py`.

**Factual status:** **shipped.** Remaining work is documentation drift (in-tree status line).

**Recommendation:** treat as already shipped; optional docs-only node to flip RFC status. Not an AC-20 feature node.

## GAP-5 — Open GitHub contract RFCs

### GAP-5a — #1675 L4 `/v1/runtime/*`

- Issue [#1675](https://github.com/Valynt/Fabric_4L/issues/1675) **open**, `needs-council-review`.
- Implementation PR [#1666](https://github.com/Valynt/Fabric_4L/pull/1666) **merged** 2026-09-04 (additive `/v1/runtime/*`, 79 files).

**Factual status:** code shipped; council ratification open.

**Recommendation:** council-ratify; do not re-implement in AC-20.

### GAP-5b — #1636 registries + `x-tenant-scope`

- Issue [#1636](https://github.com/Valynt/Fabric_4L/issues/1636) **open**.
- Implementation PR [#1635](https://github.com/Valynt/Fabric_4L/pull/1635) **open** (123 files, +7386; mergeable_state unknown).

**Factual status:** not on main. Additive metadata.

**Recommendation:** land #1635 outside AC-20 (already sized) **or** include as one `contract-metadata` node after council. Do not rewrite it inside the pipeline.

### GAP-5c — #1613 billing ownership in L4

- Issue [#1613](https://github.com/Valynt/Fabric_4L/issues/1613) **open**, still describes keeping L7 as a compatibility contract.
- Implementation PR [#1596](https://github.com/Valynt/Fabric_4L/pull/1596) **merged** 2026-09-03: **deleted** `services/layer7-billing/`; “no customers / never launched”; COMPAT-L4-003 archived.

**Factual status:** runtime ownership is already L4. RFC text is **superseded by the merge**. Council issue is stale.

**Recommendation:** close #1613 as superseded; not an AC-20 node.

## GAP-6 — Neo4jVariableRegistry unscoped

**Evidence:** `services/layer4-agents/src/layer4_agents/services/variable_registry_service.py` on `4bb4e14`. Cypher `CREATE`/`MATCH`/`search` has **no `tenant_id` predicate**. Confirms Slice T MEDIUM. PR [#1684](https://github.com/Valynt/Fabric_4L/pull/1684) is docs-only audit.

**Recommendation:** separate security PR (`security-narrow` budget), not an AC-20 product node. Human still chooses ship-now vs residual risk.

## GAP-7 — Document-export tenant ownership

Open PR [#1669](https://github.com/Valynt/Fabric_4L/pull/1669). **Recommendation:** leave to that PR.

## GAP-8 — L5 `claim.approve` multi-model authz

Open PR [#1650](https://github.com/Valynt/Fabric_4L/pull/1650), +5963 / 37 files, mergeable **behind**. **Recommendation:** leave to that PR (already over `security-narrow` / `service-feature` budgets).

## GAP-9 — pnpm 10.18.1 vs P0 #1639 `>=10.34.5`

Issue [#1639](https://github.com/Valynt/Fabric_4L/issues/1639) open. PR [#1645](https://github.com/Valynt/Fabric_4L/pull/1645) open, mergeable **dirty**, 65 files. **Lane:** prerequisite maintenance. **Recommendation:** land #1645 outside AC-20; do not silently rewrite pins in this pipeline.

## GAP-10 — Python 3.11.15 vs 3.11.10

`.python-version` = 3.11.15; `.tool-versions` = `python 3.11.10`. Both committed. **No evidence which is canonical.** **Recommendation:** pick one pin in writing; then it is prereq maintenance.

## GAP-11 — `apps/web/pnpm-lock.yaml`

File exists (499808 bytes) beside root lockfile. AGENTS.md policy: no package-local lockfiles. **Recommendation:** delete **or** amend policy. Not an AC-20 feature.

## GAP-12 — Overdue CDR rows (target 2026-08-31; today 2026-09-05)

Active (not struck) in `docs/governance/compatibility-debt-registry.md`:

| ID | Path | Owner column | Target |
|---|---|---|---|
| COMPAT-L1-001 | `.../layer1_ingestion/api/routes/compatibility.py` | layer1-ingestion | 2026-08-31 |
| COMPAT-L3-001 | `.../compat_aliases.py` | layer3-knowledge | 2026-08-31 |
| COMPAT-L3-002 | `.../entity_compat.py` | layer3-knowledge | 2026-08-31 |
| COMPAT-L3-005 | `.../compat_metrics.py` | layer3-knowledge | 2026-08-31 |
| COMPAT-WEB-004 | `userTierStore.ts` | web-platform | 2026-08-31 |
| COMPAT-WEB-018 | `RightRail.tsx` | web-platform | 2026-08-31 |
| COMPAT-WEB-019 | openapi-drift contract allowance | web-platform | 2026-08-31 |
| COMPAT-WEB-020 | `LegacyTabs.tsx` | web-platform | 2026-08-31 |
| COMPAT-L4-001 | `src/api/routes/frontend_compat.py` | layer4-agents | 2026-08-31 |
| COMPAT-L4-004 | package-mirror `frontend_compat.py` | layer4-agents | 2026-08-31 |

Still in date (not overdue): COMPAT-L5-002 (2026-09-30), COMPAT-WEB-003 (2026-09-30), several WEB/L3 rows to 2026-12-31 or 2027-06-30.

**Each row needs extend / remove-now / keep-until-named-consumer.** Not one DAG node.

## GAP-13 — Skills path promotion #1683 vs FAB-106

PR [#1683](https://github.com/Valynt/Fabric_4L/pull/1683) **open**, mergeable **blocked**, labels `compat-shim-change` + `compat-owner-ack`. PR body: FAB-106 is a **different** path (`services/layer4-agents/src/skills/`) and is untouched; land S independently. **Recommendation:** leave to #1683.

## GAP-14 — L1 idempotency / terminal / robots skips

Ticketed TODOs/DONE-with-pending-tests on main (see `repo_map.json`). Sibling [#1663](https://github.com/Valynt/Fabric_4L/pull/1663) open for stuck-job metrics. **Lane:** test-debt / prereq. **Recommendation:** do not let AC-20 “make tests pass” by editing frozen tests.

## GAP-15 — L4 skipped suites (#1593)

Issue [#1593](https://github.com/Valynt/Fabric_4L/issues/1593). Skips named VF-L4-AUTH-DEBT-001, VF-L4-AUDIT-DEBT-001, deferred permission/usage suites. **Unknown without job logs whether these are infra or product holes.** **Recommendation:** classify each skip as infra vs behavior before any Step 3 harness; out of AC-20 until classified.

## GAP-16 — L3 Neo4j session lifecycle

`TODO(lifecycle)` at `dependencies_tenant_secured.py:336`. PR [#1661](https://github.com/Valynt/Fabric_4L/pull/1661) **open**, +116/5 files, mergeable **behind**. **Recommendation:** leave to #1661.

## GAP-17 — S5-2 / S5-3 / S5-4

From `docs/governance/audit-remediation-sprint-register.md` status `requires implementation`:

| ID | Item | Owner team | Evidence required |
|---|---|---|---|
| S5-2 | Install ArgoCD and validate sync | Platform Infrastructure | Functional manifests + sync evidence |
| S5-3 | WAL-G placeholders + restore drill | Platform Infrastructure | Restore drill artifact |
| S5-4 | OpenTelemetry tracing migration | Observability | Live trace receipt from named services |

**Lane:** external/ops. S5-4 text still mentions Layer 7, which #1596 deleted — the register row is stale on that point.

## GAP-18 — Launch P0/P1 environment evidence

`docs/launch/launch-blocker-register.md`: repository-owned P0/P1 **code** blockers claimed resolved 2026-06-16. Remaining items are `REQUIRES_ENVIRONMENT` (P0-001 4/7 journeys, P0-002 rollback drill, P1-001 receivers, P1-002 telemetry, P1-003 billing provider, P1-004 perf, P1-008 SLO, P1-009 live LLM). P0-003 already scoped out of Core GA (Clerk).

**Lane:** release requirements. **Recommendation:** not AC-20 code. Core-GA vs paid-GA vs repo-only is a human launch decision.

## GAP-19 — SDK `vf auth login` loopback

`TODO(VF-SDK-AUTH-DEBT-001)` on main. Replacement PR [#1681](https://github.com/Valynt/Fabric_4L/pull/1681) **open**, 2 files, +250, mergeable **blocked**. Ballooned #1624 should close once #1681 lands. **Recommendation:** leave to #1681.
