# Implementation-status evidence (GAP factual questions)

**Anchor:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**Method:** GitHub file/search + issue/PR metadata + job logs. No product intent inferred.  
**Options** are labeled as such; they are not decisions and not issue closures.

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

**Option (not a choice):** if any Slice 2 work is in AC-20, contract §6 names 1a as the smallest next step. 1b–1g are not one node.

## GAP-2 — Q3/Q4 ROADMAP.md

Roadmap items are a product schedule, not tickets. **Option:** out of AC-20 unless separately ticketed and signed.

## GAP-3 — RFC-001 Formula Scenario endpoint (rewritten)

**Correction:** the previous packet reported the endpoint absent. It is **registered and implemented**. Full evidence: [GAP-3.md](./GAP-3.md).

Short form:

- `POST /formulas/scenario` → `formulas.calculate_scenario` is on the L3 router.
- RFC-001 (Approved 2026-04-27, council decision **in the RFC file**) specified `formula_id` + `adjustments[{variable_id,new_value}]`.
- Shipped Pydantic uses `base_case_id` + `adjustments[{name,value,original_value}]` + optional client `base_case_data`.
- FE contract test uses a third schema (`formula_id` + `scenarios[]`).
- OpenAPI tree on this SHA has **0** `/formulas/scenario` hits.
- Path is on the **public unauthenticated allowlist**. Handler does not call Neo4j; missing payload → zero-value 200. FE hook does not send `base_case_data`.
- Duplicate endpoint: **out of bounds** unless you write that choice.

**Options:** schema A/B/C/D, OpenAPI publish, tenant lookup vs public, 200-zeros vs 400. See GAP-3.md §2–4.

## GAP-4 — RFC-002 journey_id

**Cited:**

- Implementation PR [#1385](https://github.com/Valynt/Fabric_4L/pull/1385) **merged** 2026-08-21.
- RFC markdown PR [#1543](https://github.com/Valynt/Fabric_4L/pull/1543) **merged**.
- Tracking issue [#1387](https://github.com/Valynt/Fabric_4L/issues/1387) **closed completed** 2026-08-28 by `valyntxyz`; `closed_by_pull_requests` = #1543 MERGED.
- In-tree RFC-002 header still says “Pending Council Review.” The closed issue still has label `needs-council-review`.
- Code search: `journey_id` present in `agent_stream.py`, `conversation.py`.

**Factual:** implementation is on main (cited merge). **Not factual:** Contract Council ratification. No council minutes were found. The issue close is an issue-close, not a council document.

**Option:** docs-only RFC header flip, and/or council paperwork. Not an AC-20 feature node unless you write that.

## GAP-5 — Open GitHub contract RFCs

### GAP-5a — #1675 L4 `/v1/runtime/*`

- Issue [#1675](https://github.com/Valynt/Fabric_4L/issues/1675) **open**, `needs-council-review`, `closed_by_pull_requests.total_count = 0`.
- Implementation PR [#1666](https://github.com/Valynt/Fabric_4L/pull/1666) **merged** 2026-09-04.

**Factual:** code shipped; council issue open. **Option:** council acts on #1675. Agents will not close or ratify.

### GAP-5b — #1636 registries + `x-tenant-scope`

- Issue [#1636](https://github.com/Valynt/Fabric_4L/issues/1636) **open**.
- Implementation PR [#1635](https://github.com/Valynt/Fabric_4L/pull/1635) **open** (123 files).

**Factual:** not on main. **work_class:** `external_impl_owner`.

### GAP-5c — #1613 billing ownership in L4

- Issue [#1613](https://github.com/Valynt/Fabric_4L/issues/1613) **open**, `needs-council-review`, `closed_by_pull_requests.total_count = 0`. RFC body requires preserving Layer 7 as a time-bounded compatibility contract and names evidence council must see before merge.
- Implementation PR [#1596](https://github.com/Valynt/Fabric_4L/pull/1596) **merged** 2026-09-03 and **deleted** `services/layer7-billing/`.

**Factual:** a merge happened that conflicts with the still-open RFC text. **Not factual:** “#1613 is superseded / should be closed.” There is no cited council close.

**Option:** leave #1613 to council with the conflict noted.

## GAP-6 — Neo4jVariableRegistry unscoped

**Evidence:** `services/layer4-agents/src/layer4_agents/services/variable_registry_service.py` on `4bb4e14`. Cypher `CREATE`/`MATCH`/`search` has **no `tenant_id` predicate**. PR [#1684](https://github.com/Valynt/Fabric_4L/pull/1684) is docs-only.

**Option:** separate security PR, AC-20 node, or residual risk. Human chooses.

## GAP-7 / GAP-8 / GAP-13 / GAP-16 / GAP-19 — external implementation ownership

| ID | Open PR | work_class |
|---|---|---|
| GAP-7 | [#1669](https://github.com/Valynt/Fabric_4L/pull/1669) | `external_impl_owner` |
| GAP-8 | [#1650](https://github.com/Valynt/Fabric_4L/pull/1650) (+5963 / 37 files, behind) | `external_impl_owner` |
| GAP-13 | [#1683](https://github.com/Valynt/Fabric_4L/pull/1683) (blocked; PR body says FAB-106 is a different path) | `external_impl_owner` |
| GAP-16 | [#1661](https://github.com/Valynt/Fabric_4L/pull/1661) (behind) | `external_impl_owner` |
| GAP-19 | [#1681](https://github.com/Valynt/Fabric_4L/pull/1681) (blocked; 2 files) | `external_impl_owner` |

**Option:** leave to those PRs, or pull a row into AC-20 in writing (size may trip GATE-2).

## GAP-9 / 10 / 11 — toolchain (prerequisite maintenance)

- GAP-9: [#1639](https://github.com/Valynt/Fabric_4L/issues/1639) open; [#1645](https://github.com/Valynt/Fabric_4L/pull/1645) open, mergeable dirty.
- GAP-10: `.python-version` = 3.11.15; `.tool-versions` = `python 3.11.10`. **No cited canonical pin.**
- GAP-11: `apps/web/pnpm-lock.yaml` exists; AGENTS.md forbids package-local lockfiles.

## GAP-12 — Overdue CDR rows

Active (not struck) in `docs/governance/compatibility-debt-registry.md`, target 2026-08-31: COMPAT-L1-001, L3-001, L3-002, L3-005, WEB-004, WEB-018, WEB-019, WEB-020, L4-001, L4-004.

Each row needs extend / remove-now / keep-until-named-consumer. Not one DAG node.

## GAP-14 / GAP-15 — test debt

GAP-14: mixed TODO/DONE-pending-tests on main; sibling [#1663](https://github.com/Valynt/Fabric_4L/pull/1663) open.  
GAP-15: [#1593](https://github.com/Valynt/Fabric_4L/issues/1593) skips named VF-L4-AUTH-DEBT-001, VF-L4-AUDIT-DEBT-001, deferred permission/usage suites. Infra vs behavior **not classified** from job logs in this packet.

## GAP-17 — S5-2 / S5-3 / S5-4

From `docs/governance/audit-remediation-sprint-register.md` status `requires implementation`. **work_class:** `release_requirement` (ops). S5-4 text still mentions Layer 7 after #1596 deleted that service — register drift, not a council decision.

## GAP-18 — Launch P0/P1 environment evidence

`docs/launch/launch-blocker-register.md`: remaining items `REQUIRES_ENVIRONMENT`.

P0-003: `docs/launch/sso-core-ga-scope-decision.md` **body** records Option B (SSO not in Core GA) dated 2026-06-16. The signature table is `_TBD_` for Product, Identity, Security, and Release Management. The file says: *“Names and countersignatures must be filled by the responsible owners before this decision is authoritative.”*

**Not factual:** “already scoped out of Core GA” as a binding decision. **Factual:** an unsigned decision draft exists and names Option B.

**Option:** countersign, choose Option A, or ignore. Agents will not close P0-003.
