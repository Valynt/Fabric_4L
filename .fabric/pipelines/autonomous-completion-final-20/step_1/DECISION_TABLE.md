# GATE-1 decision table (unsigned)

**Anchor:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**Disposition:** DEFER — `spec_gaps_signed_off: false`  
**Operator GAP-0:** **block**  
**Budget policy:** `policies/node-budget.v1.json` (`1.0.0-proposed`, not in force until you approve it)

Fill the last column. Agents will not.

**Lane** values (mutually exclusive per sub-id):

| Lane | Meaning |
|---|---|
| `already_shipped` | On main; do not re-implement |
| `council_only` | Code may exist; Contract Council is the remaining act |
| `open_pr_outside_ac20` | Dedicated PR already owns it |
| `ac20_candidate_impl` | Could become a DAG node *after* GATE-1 APPROVE **and** GAP-0 unblocked |
| `prerequisite_maintenance` | 80% / toolchain / test-debt; not “final 20% product” |
| `external_environment` | Needs staging/creds/ops evidence |
| `deferred_product` | Named out of this slice unless you pull it in |
| `release_requirement` | Launch/GA evidence, not a code node |
| `docs_drift` | Status text disagrees with git/GitHub |

**Human choice** is the only column that unblocks Step 2. Recommendations are optional and may be ignored.

| ID | Sub | Title | Factual status | Lane | CODEOWNERS owner | External prereq | Open PR/issue | Proposed budget profile | Recommendation | Human choice (in / out / other) |
|---|---|---|---|---|---|---|---|---|---|---|
| GAP-0 | — | Existing suite red on 80% | Three confirmed PR Checks fails (Docker/e2e/runtime-contract) + six Prod Readiness fails. `02-code-quality-and-tests` **not confirmed** as independent fail on re-query. | `prerequisite_maintenance` | `@value-fabric/sre-leads` `@value-fabric/qa-leads` | Docker/services-up CI | runs 33970450342, 33970450317 | n/a (halt class) | Keep **block** until the three confirmed jobs are green; separately classify Prod Readiness as release (GAP-18). | **block** (already set) |
| GAP-1 | a | Studio backend projection adapter | Slice 1 fixture-only; contract §6 names this as smallest next step | `ac20_candidate_impl` *if signed in* | web + backend-leads | L4/mission projection API must exist or be built with it | FE-VOS-STUDIO-001 | `frontend-slice` 500/15 plus a L4 `service-feature` 400/12 if API is new | Include only this Slice 2 item if any | |
| GAP-1 | b | Mission command channel | `COMMAND_BACKEND_NOTICE`; no command API | `deferred_product` unless signed | agent-team + frontend-leads | mission backend | — | `service-feature` | Defer (depends on 1a) | |
| GAP-1 | c | Activity event streaming | Projected trail only | `deferred_product` | agent-team | event stream | — | `service-feature` | Defer | |
| GAP-1 | d | Calc service integration | Impact read-only in FE | `deferred_product` | backend-leads | calc service | — | `service-feature` | Defer | |
| GAP-1 | e | Generative lens rendering | Thesys/OpenUI **not adopted**; static fallback shipped | `deferred_product` | frontend-leads + architects | product reversal of “not adopted” | — | n/a | Keep out unless product reverses DEC | |
| GAP-1 | f | Publication workflow | Labels only | `deferred_product` | architects / governance | — | — | `service-feature` | Defer | |
| GAP-1 | g | Rewind/undo events | UI gated on `allowedActions` | `deferred_product` | agent-team | 1b | — | `service-feature` | Defer (with 1b) | |
| GAP-2 | — | ROADMAP Q3/Q4 | Schedule, not tickets | `deferred_product` | maintainers | — | ROADMAP.md | n/a | Out of AC-20 | |
| GAP-3 | — | RFC-001 `POST /formulas/scenario` | RFC **Approved**; OpenAPI path **absent**; FE hook present | `ac20_candidate_impl` *or* close RFC | L3 graph-specialists + frontend-leads | none for the endpoint itself | RFC-001 file | `service-feature` 400/12 | Implement as specified **or** close/supersede | |
| GAP-4 | — | RFC-002 journey_id | **Shipped** #1385; issue #1387 closed; in-tree RFC header stale | `already_shipped` + optional `docs_drift` | L4 agent-team | none | #1385 merged, #1387 closed, #1543 merged | `evidence-docs` if docs-only | Out of AC-20 as feature; optional docs fix | |
| GAP-5 | a | RFC #1675 runtime paths | Code **merged** #1666; issue still open | `council_only` | L4 + contracts | Contract Council ≥2 domains | #1675 open, #1666 merged | n/a | Ratify; do not re-implement | |
| GAP-5 | b | RFC #1636 registries | PR #1635 open, not on main | `open_pr_outside_ac20` *or* `council_only` after merge | architects + backend-leads | Contract Council | #1636, #1635 | already 123 files — over `contract-metadata` 40-file cap | Land #1635 outside AC-20 | |
| GAP-5 | c | RFC #1613 billing L4 | #1596 **merged** (L7 deleted); RFC text obsolete | `already_shipped` + `council_only` (close issue) | L4 + architects | none | #1613 open, #1596 merged | n/a | Close #1613 as superseded | |
| GAP-6 | — | Neo4jVariableRegistry unscoped | Confirmed no tenant predicate in Cypher | `ac20_candidate_impl` *or* separate security PR | L4 + security-leads | none | #1684 docs-only | `security-narrow` 250/8 | Separate security PR; not product 20% | |
| GAP-7 | — | Document-export tenant ownership | Owned by open PR | `open_pr_outside_ac20` | L4 + security-leads | none | #1669 | already scoped | Leave to #1669 | |
| GAP-8 | — | L5 claim.approve authz | Owned by open PR; 37 files / +5963 | `open_pr_outside_ac20` | L5 + security-leads | none | #1650 (behind) | already over budget | Leave to #1650 | |
| GAP-9 | — | pnpm ≥10.34.5 | P0 #1639; PR dirty | `prerequisite_maintenance` | ci + maintainers | lockfile blast #1643/#1644 | #1639, #1645 | `toolchain` 300/25 | Land #1645 outside AC-20 | |
| GAP-10 | — | Python 3.11.15 vs 3.11.10 | Both pins committed; canonical unknown | `prerequisite_maintenance` | maintainers / DevEx | none | — | `toolchain` | You pick the canonical pin | |
| GAP-11 | — | apps/web/pnpm-lock.yaml | Exists; contradicts AGENTS.md | `prerequisite_maintenance` | frontend-leads + maintainers | none | — | `toolchain` | Delete lockfile **or** amend policy | |
| GAP-12 | L1-001 | compat route wrapper | Overdue 2026-08-31 | `ac20_candidate_impl` *if* remove-now | L1 | consumer inventory | CDR | `service-feature` per row | Per-row: extend / remove / keep | |
| GAP-12 | L3-001 | compat_aliases | overdue | same | L3 | consumer inventory | CDR | `service-feature` | Per-row | |
| GAP-12 | L3-002 | entity_compat | overdue | same | L3 | consumer inventory | CDR | `service-feature` | Per-row | |
| GAP-12 | L3-005 | compat_metrics | overdue | same | L3 | — | CDR | `service-feature` | Per-row | |
| GAP-12 | WEB-004 | userTierStore | overdue | same | web | — | CDR | `frontend-slice` | Per-row | |
| GAP-12 | WEB-018 | RightRail AG-UI props | overdue | same | web | — | CDR | `frontend-slice` | Per-row | |
| GAP-12 | WEB-019 | OpenAPI drift allowance | overdue | same | web + contracts | — | CDR | `contract-metadata` | Per-row | |
| GAP-12 | WEB-020 | LegacyTabs | overdue | same | web | — | CDR | `frontend-slice` | Per-row | |
| GAP-12 | L4-001 | frontend_compat (src/api) | overdue | same | L4 | — | CDR | `service-feature` | Per-row | |
| GAP-12 | L4-004 | frontend_compat package mirror | overdue | same | L4 | likely same consumers as L4-001 | CDR | `service-feature` | Per-row; maybe one node with L4-001 | |
| GAP-13 | — | agents/skills promotion | Open PR with shim CDR | `open_pr_outside_ac20` | architects + L4 | FAB-106 merge order (PR says independent) | #1683 | already 76 files | Leave to #1683 | |
| GAP-14 | — | L1 skip/TODO debt | Mixed TODO vs DONE-pending-tests | `prerequisite_maintenance` | L1 + qa-leads | none | #1663 (metrics subset) | `test-debt` 350/10 | Close tests or keep known skips; not product 20% | |
| GAP-15 | — | L4 skipped suites #1593 | Infra vs behavior **not classified** | `prerequisite_maintenance` until classified | L4 + qa-leads | extra auth setup per skip message | #1593 | `test-debt` | Classify first; out until then | |
| GAP-16 | — | L3 Neo4j session close | Open PR | `open_pr_outside_ac20` | L3 graph-specialists | none | #1661 | already 5 files | Leave to #1661 | |
| GAP-17 | S5-2 | ArgoCD install + sync | `requires implementation` | `external_environment` | sre-leads + infrastructure-leads | cluster | audit register | `ops-manifest` | Out of AC-20 code DAG | |
| GAP-17 | S5-3 | WAL-G + restore drill | `requires implementation` | `external_environment` | sre-leads | backup env | audit register | `ops-manifest` | Out; evidence artifact, not feature | |
| GAP-17 | S5-4 | OTel live traces | `requires implementation`; text still mentions L7 (stale post-#1596) | `external_environment` | backend-leads + sre | reachable tracing backend | audit register | `ops-manifest` | Out; update register L7 mention | |
| GAP-18 | P0-001 | 4/7 live E2E journeys | REQUIRES_ENVIRONMENT | `release_requirement` | qa-leads | staging | launch-blocker-register | n/a | Launch decision, not DAG | |
| GAP-18 | P0-002 | Rollback/restore drill | REQUIRES_ENVIRONMENT | `release_requirement` | sre-leads | prod-like env | same | n/a | Launch decision | |
| GAP-18 | P0-003 | Enterprise SSO | Already **scoped out of Core GA** | `release_requirement` | security-leads | IdP | `sso-core-ga-scope-decision.md` | n/a | Keep scoped out unless paid-GA pulled in | |
| GAP-18 | P1-* | receivers, telemetry, billing provider, perf, SLO, live LLM | REQUIRES_ENVIRONMENT | `release_requirement` | sre / observability / billing / AI | providers | launch-blocker-register | n/a | Paid-GA vs Core-GA is yours | |
| GAP-19 | — | SDK OIDC loopback | Open replacement PR; 2 files | `open_pr_outside_ac20` | backend-leads (sdk) | local port 8080 for manual | #1681 (close #1624 after) | already under `service-feature` | Leave to #1681 | |

## Suggested sign-off skeleton (still blank — do not treat as signed)

```
GATE-1: not signed
GAP-0: block   # already set; remains in force
In-scope AC-20 (recommendation only): GAP-1a, GAP-3   # you may delete both
Out-of-scope: all other rows
Budgets: policies/node-budget.v1.json version 1.0.0-proposed
Owners: CODEOWNERS teams in this table
```

No row above is in-scope until you write it in.
