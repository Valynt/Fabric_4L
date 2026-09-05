# GATE-1 decision table (unsigned)

**Anchor / freeze:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**Disposition:** DEFER — `spec_gaps_signed_off: false`  
**Operator GAP-0:** **block**  
**Budget policy:** `policies/node-budget.v1.json` (`1.1.0-proposed`, not in force)

Fill the last column. Agents will not. Recommendations are options, not closures.

**work_class** (mutually exclusive per sub-id):

| work_class | Meaning |
|---|---|
| `blocking_prereq` | Must be resolved (or waived in writing) before AC-20 Steps 2–6. Not a product node. |
| `external_impl_owner` | An open PR/issue already owns implementation. AC-20 does not take it unless you move it. |
| `release_requirement` | Launch/GA evidence. Not a code DAG node. |
| `council_open` | Contract RFC issue still open; no cited council close. |
| `ac20_candidate` | Could become a DAG node *after* GATE-1 APPROVE **and** GAP-0 unblocked **and** Step 0 complete or waived. |
| `deferred_product` | Named out of this slice unless you pull it in. |
| `docs_drift` | Git/GitHub disagree with in-tree status text. Not a feature. |

**Cited vs inferred:** “close the issue”, “ratify”, “already scoped out of Core GA” are **not** written as facts unless a cited signed decision exists. Open council issues stay `council_open`.

| ID | Sub | Title | Factual status (cited) | work_class | CODEOWNERS / impl owner | Blocking prereq? | Release req? | Open PR/issue | Proposed budget profile | Options (not a choice) | Human choice (in / out / other) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GAP-0 | — | Existing suite red on 80% | PR Checks 45/45: 4 underlying fails + Layer 3 cancelled + 2 aggregates. Prod Readiness 16/16: 4 underlying + 2 aggregates. See `step_0/ci_inventory.json`. | `blocking_prereq` | `@value-fabric/sre-leads` `@value-fabric/qa-leads` | **yes** (operator block) | no (halt class) | runs 33970450342, 33970450317 | n/a | Keep block until named underlying jobs + L3 cancellation are green, or write a waiver naming the jobs. | |
| GAP-1 | a | Studio backend projection adapter | FE-VOS-STUDIO-001 §6 names this as smallest next step; Slice 1 fixture-only | `ac20_candidate` *if signed in* | web + backend-leads | no | no | FE-VOS-STUDIO-001 | `frontend-slice` 500/15 + L4 `service-feature` 400/12 if API is new | Include 1a only / include more / out | |
| GAP-1 | b | Mission command channel | `COMMAND_BACKEND_NOTICE`; no command API | `deferred_product` unless signed | agent-team + frontend-leads | no | no | — | `service-feature` | Defer / pull in with 1a | |
| GAP-1 | c | Activity event streaming | Projected trail only | `deferred_product` | agent-team | no | no | — | `service-feature` | Defer / pull in | |
| GAP-1 | d | Calc service integration | Impact read-only in FE | `deferred_product` | backend-leads | no | no | — | `service-feature` | Defer / pull in | |
| GAP-1 | e | Generative lens rendering | Thesys/OpenUI **not adopted**; static fallback shipped (contract text) | `deferred_product` | frontend-leads + architects | no | no | — | n/a | Keep out unless product reverses the contract DEC | |
| GAP-1 | f | Publication workflow | Labels only | `deferred_product` | architects | no | no | — | `service-feature` | Defer / pull in | |
| GAP-1 | g | Rewind/undo events | UI gated on `allowedActions` | `deferred_product` | agent-team | no | no | — | `service-feature` | Defer (with 1b) / pull in | |
| GAP-2 | — | ROADMAP Q3/Q4 | Schedule, not tickets | `deferred_product` | maintainers | no | no | ROADMAP.md | n/a | Out unless separately ticketed | |
| GAP-3 | a | Canonical scenario schema | Route **exists**. RFC-001 vs handler vs FE test vs contract-map diverge. See `GAP-3.md` | `ac20_candidate` *if signed in* | L3 graph-specialists + frontend-leads + contracts | no | no | RFC-001 file | `service-feature` 400/12 | Pick schema A/B/C/D in GAP-3.md. Do not add a second path. | |
| GAP-3 | b | OpenAPI path missing | `contracts/openapi` has 0 hits for `/formulas/scenario` on freeze SHA; RFC §3 required it | `ac20_candidate` *if signed in* | contracts | no | no | RFC-001 | `contract-metadata` | Publish OpenAPI to match 3a / leave unpublished | |
| GAP-3 | c | Tenant-scoped authoritative resolution | RFC §5 tenant Bearer + formula ownership. Handler is on **public allowlist**; `base_case_data` from client bypasses lookup; no Neo4j query despite comment | `ac20_candidate` *or* separate security PR | L3 + security-leads | no (unless you classify as security block) | no | allowlist + formulas.py | `security-narrow` 250/8 | Keep public+client data / require tenant lookup / overlay with threat model | |
| GAP-3 | d | Zero-value fallback | Missing `base_case_data` → 200 + zeros + warning. FE hook does not send `base_case_data`. Route docs say 400 | `ac20_candidate` *if signed in* | L3 | no | no | formulas.py + scenario_engine.py | `service-feature` | Keep zeros / 400 / implement the lookup | |
| GAP-3 | e | Hook registry unmapped | `endpoint-hook-registry.json` status `unmapped`; hook file exists | `docs_drift` | web | no | no | endpoint-hook-registry.json | `evidence-docs` | Flip registry / leave | |
| GAP-4 | — | RFC-002 journey_id | **Code** on main (#1385 merged). Issue [#1387](https://github.com/Valynt/Fabric_4L/issues/1387) **closed completed** by `valyntxyz`, closing PR [#1543](https://github.com/Valynt/Fabric_4L/pull/1543) MERGED. In-tree RFC header still “Pending Council Review”. Label `needs-council-review` remains on the closed issue. **No council minutes found.** | `docs_drift` + optional `council_open` | L4 agent-team | no | no | #1385 merged, #1387 closed, #1543 merged | `evidence-docs` if docs-only | Treat code as shipped (cited PRs). Docs-only RFC header flip is a separate choice. Do not infer council ratification from the issue close. | |
| GAP-5 | a | RFC #1675 runtime paths | PR [#1666](https://github.com/Valynt/Fabric_4L/pull/1666) **merged**. Issue [#1675](https://github.com/Valynt/Fabric_4L/issues/1675) **open**, `needs-council-review`, `closed_by_pull_requests.total_count=0` | `council_open` | L4 + contracts | no | no | #1675 open, #1666 merged | n/a | Council acts on #1675. Agents will not close or ratify. Do not re-implement. | |
| GAP-5 | b | RFC #1636 registries | PR [#1635](https://github.com/Valynt/Fabric_4L/pull/1635) **open** (123 files). Issue #1636 **open** | `external_impl_owner` | architects + backend-leads | no | no | #1636, #1635 | already 123 files — over `contract-metadata` 40-file cap | Leave to #1635 / pull into AC-20 (would trip GATE-2) | |
| GAP-5 | c | RFC #1613 billing L4 | Issue [#1613](https://github.com/Valynt/Fabric_4L/issues/1613) **open**, `needs-council-review`, `closed_by_pull_requests.total_count=0`. RFC text requires keeping L7 as compatibility. PR [#1596](https://github.com/Valynt/Fabric_4L/pull/1596) **merged** and deleted `services/layer7-billing/`. That merge is cited; it is **not** a council close of #1613. | `council_open` | L4 + architects | no | no | #1613 open, #1596 merged | n/a | Present the conflict to council. Do not close #1613 from this pipeline. | |
| GAP-6 | — | Neo4jVariableRegistry unscoped | Cypher has no tenant predicate. #1684 docs-only | `ac20_candidate` *or* separate security PR | L4 + security-leads | no | no | #1684 docs-only | `security-narrow` 250/8 | Separate security PR / AC-20 node / residual risk | |
| GAP-7 | — | Document-export tenant ownership | Open PR owns it | `external_impl_owner` | L4 + security-leads | no | no | #1669 | already scoped | Leave to #1669 / pull in | |
| GAP-8 | — | L5 claim.approve authz | Open PR owns it; 37 files / +5963 | `external_impl_owner` | L5 + security-leads | no | no | #1650 (behind) | already over budget | Leave to #1650 / pull in (GATE-2) | |
| GAP-9 | — | pnpm ≥10.34.5 | P0 #1639; PR dirty | `blocking_prereq` (toolchain) | ci + maintainers | yes if you treat P0 as freeze | no | #1639, #1645 | `toolchain` 300/25 | Land #1645 outside AC-20 / waive pin / change freeze | |
| GAP-10 | — | Python 3.11.15 vs 3.11.10 | Both pins committed; **no cited canonical pin** | `blocking_prereq` | maintainers / DevEx | yes for freeze identity | no | — | `toolchain` | You pick the canonical pin in writing | |
| GAP-11 | — | apps/web/pnpm-lock.yaml | Exists; contradicts AGENTS.md | `blocking_prereq` | frontend-leads + maintainers | policy, not suite-red | no | — | `toolchain` | Delete lockfile **or** amend policy | |
| GAP-12 | * | Overdue CDR rows | Each row overdue 2026-08-31; listed in SPEC_GAPS | `deferred_product` per row unless signed | per CDR owner | no | no | CDR | `service-feature` / `frontend-slice` / `contract-metadata` | Per-row: extend / remove / keep-until-named-consumer | |
| GAP-13 | — | agents/skills promotion | PR #1683 merged; `agents/skills/` is canonical and `.agent/skills/MOVED.md` preserves the COMPAT-SKILLS-001 shim | `docs_drift` | architects + L4 | no | no | #1683 merged | n/a | No AC-20 node; track shim removal through COMPAT-SKILLS-001 | |
| GAP-14 | — | L1 skip/TODO debt | Mixed TODO vs DONE-pending-tests | `blocking_prereq` (test-debt) | L1 + qa-leads | no unless you fold into GAP-0 | no | #1663 (metrics subset) | `test-debt` 350/10 | Close tests / keep known skips | |
| GAP-15 | — | L4 skipped suites #1593 | Infra vs behavior **not classified** | `blocking_prereq` until classified | L4 + qa-leads | no until classified | no | #1593 | `test-debt` | Classify first; out until then | |
| GAP-16 | — | L3 Neo4j session close | Open PR | `external_impl_owner` | L3 graph-specialists | no | no | #1661 | already 5 files | Leave to #1661 / pull in | |
| GAP-17 | S5-2 | ArgoCD install + sync | audit register `requires implementation` | `release_requirement` (ops) | sre-leads + infrastructure-leads | no | **yes** | audit register | `ops-manifest` | Out of AC-20 code DAG | |
| GAP-17 | S5-3 | WAL-G + restore drill | same | `release_requirement` | sre-leads | no | **yes** | audit register | `ops-manifest` | Out | |
| GAP-17 | S5-4 | OTel live traces | same; register text still mentions L7 (stale vs #1596 merge, not a council close) | `release_requirement` | backend-leads + sre | no | **yes** | audit register | `ops-manifest` | Out; register L7 mention is docs drift | |
| GAP-18 | P0-001 | 4/7 live E2E journeys | launch-blocker-register `REQUIRES_ENVIRONMENT` | `release_requirement` | qa-leads | no | **yes** | launch-blocker-register | n/a | Launch decision, not DAG | |
| GAP-18 | P0-002 | Rollback/restore drill | `REQUIRES_ENVIRONMENT` | `release_requirement` | sre-leads | no | **yes** | same | n/a | Launch decision | |
| GAP-18 | P0-003 | Enterprise SSO | `docs/launch/sso-core-ga-scope-decision.md` **text** says Option B. Signers are `_TBD_`. File states it is **not authoritative until countersigned**. Waiver WVR-2026-06-15-003 is referenced, not re-read here as a substitute signature. | `release_requirement` | security-leads | no | **yes** | unsigned decision file | n/a | Countersign Option B / choose Option A / ignore. Do not treat as closed. | |
| GAP-18 | P1-* | receivers, telemetry, billing provider, perf, SLO, live LLM | `REQUIRES_ENVIRONMENT` | `release_requirement` | sre / observability / billing / AI | no | **yes** | launch-blocker-register | n/a | Paid-GA vs Core-GA is yours | |
| GAP-19 | — | SDK OIDC loopback | Open replacement PR; 2 files | `external_impl_owner` | backend-leads (sdk) | no | no | #1681 | already under `service-feature` | Leave to #1681 / pull in | |

## Suggested sign-off skeleton (blank — do not treat as signed)

```
GATE-1: not signed
freeze_sha: 4bb4e142c2ccbc56297de843e71534d956bb198f
reviewed_evidence_sha: <this packet head>
GAP-0: block
In-scope AC-20: (none until you write IDs)
Out-of-scope: (none until you write IDs)
Budgets: policies/node-budget.v1.json version 1.1.0-proposed   # only if you approve it
```

No row above is in-scope until you write it in. No issue is closed by this table.
