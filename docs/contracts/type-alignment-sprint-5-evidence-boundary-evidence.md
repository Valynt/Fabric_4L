# Type Alignment Sprint 5 Evidence Boundary Evidence

Author: **Manus AI**  
Date: 2026-05-05  
Repository: `bmsull560/Fabric_4L`

## Summary

Sprint 5 completed the next open type-alignment item by migrating `apps/web/src/hooks/useEvidence.ts` from cast-based response trust to **domain-owned runtime validation**. The sprint follows the same boundary pattern established by the product, ground-truth governance, and competitive-intelligence migrations: API responses enter the frontend as untrusted transport data, Zod parsers validate each response-bearing boundary, and TanStack Query publishes schema-inferred domain types to consumers.

The implementation adds `apps/web/src/lib/schemas/evidence.ts` as the evidence domain schema module, adds focused parser coverage for backend-shaped evidence payloads, and adapts the Studio evidence consumer to the parsed backend list envelope and backend evidence fields. The evidence hook no longer asserts `response.data` into local response interfaces; each query and mutation that consumes a response body now validates it before returning data to the cache or mutation success path.

## Changed Files

| File | Purpose |
|---|---|
| `apps/web/src/lib/schemas/evidence.ts` | Adds evidence Zod schemas, schema-inferred domain types, and parser functions for response-bearing case-study, stats, bulk-import, and semantic-search boundaries. |
| `apps/web/src/lib/schemas/evidence.test.ts` | Adds focused positive and negative parser tests using backend-shaped evidence fixtures and malformed payloads. |
| `apps/web/src/hooks/useEvidence.ts` | Refactors evidence query and mutation functions to parse response data instead of using unsafe response casts, while preserving exported hook type names where possible. |
| `apps/web/src/pages/studio/StudioEvidenceTab.tsx` | Updates the Studio evidence tab to consume parsed backend-shaped list envelopes and case-study fields without local array or envelope casts. |
| `docs/contracts/type-alignment-sprint-5-evidence-boundary-evidence.md` | Records Sprint 5 implementation scope, validation evidence, residual risks, and handoff recommendations. |
| `contracts/openapi/layer3-knowledge.json`, `contracts/openapi/layer4-agents.json`, `apps/web/src/api/generated/l3/index.ts`, `apps/web/src/api/generated/l4/index.ts` | Includes regenerated contract artifacts required by the rebased backend service sources so the repository contract freshness gate passes from the committed tree. |
| `apps/web/src/pages/AgentWorkflows.tsx` | Applies minimal compatibility fixes for upstream workflow request and status changes discovered during rebase validation, preserving Sprint 5 typecheck. |
| `services/layer4-agents/src/layer4_agents/api/routes/workflows.py` | Stabilizes the Layer 4 workflow type enum order so regenerated OpenAPI and frontend DTO artifacts remain deterministic across contract freshness runs. |

## Boundary Scope

Sprint 5 covers the L3 evidence hook module and every response-bearing operation that the hook exposes. Request interfaces remain hook-owned because this sprint targeted the highest-risk direction: backend response data entering frontend cache state, mutation result state, and user-facing Studio rendering.

| Boundary Area | Runtime Validation Outcome |
|---|---|
| Case-study list response | Parsed through `parseCaseStudyListResponse`, validating the `items`, `total`, `offset`, and `limit` envelope before cache publication. |
| Case-study detail response | Parsed through `parseCaseStudy`, including backend case-study metadata, products used, addressed pain signals, measured outcomes, linked products, and linked signals. |
| Case-study create and update responses | Parsed through `parseCaseStudyMutationResponse`, validating backend acknowledgement payloads before mutation success handlers invalidate evidence caches. |
| Case-study delete response | Parsed through `parseDeleteCaseStudyResponse`, validating the backend delete acknowledgement rather than discarding the response body. |
| Industry and product stats responses | Parsed through `parseEvidenceStatsResponse`, validating backend record maps of category names to non-negative counts. |
| Bulk-import response | Parsed through `parseBulkImportResponse`, including total, created count, and structured row-level errors. |
| Semantic evidence-search response | Parsed through `parseEvidenceSearchResponse`, validating query echo, result count, search result identities, reasoning text, and bounded match scores. |

## Parser Test Coverage

The new evidence parser suite follows the same positive-and-negative convention used by earlier migrated boundaries. Positive tests exercise backend-shaped payloads that match the current L3 evidence routes and service output. Negative tests deliberately pass malformed payloads that should fail fast at the trust boundary.

| Parser Suite | Positive Coverage | Negative Coverage |
|---|---|---|
| `evidence.test.ts` | Case-study detail payloads, case-study list envelopes, create/update acknowledgements, delete acknowledgements, stats maps, bulk-import envelopes, and semantic-search envelopes. | Case studies missing required identifiers, stats maps with non-numeric counts, and semantic-search match scores outside the backend-supported range. |

## Validation Evidence

Validation was run after formatting the touched TypeScript files, rebasing the Sprint 5 commit onto the updated remote `main`, and resolving rebase-discovered validation blockers introduced by upstream graph and workflow changes. A later upstream commit supplied the graph schema safety fix directly on `origin/main`; the rebased Sprint 5 commit retains only the workflow page compatibility fix needed by this branch. The contract freshness gate regenerated deterministic OpenAPI contracts and frontend DTO artifacts; those generated artifacts are included with Sprint 5 so the final gate can compare the committed tree to current backend service sources without drift. The final standard contract freshness gate completed with status code `0` after the commit was amended with the regenerated artifacts.

| Check | Result | Evidence |
|---|---:|---|
| Focused parser tests | PASS | `pnpm vitest run src/lib/schemas/products.test.ts src/lib/schemas/groundTruthGovernance.test.ts src/lib/schemas/competitiveIntel.test.ts src/lib/schemas/evidence.test.ts` completed with **4 passed files** and **44 passed tests**. |
| Frontend typecheck | PASS | `pnpm check` completed successfully in `apps/web`. |
| Evidence cast leakage check | PASS | `grep -R "response\.data as" -n src/hooks/useEvidence.ts` found no residual response-data cast leakage. |
| Contract freshness gate | PASS | `scripts/ci/check_contract_freshness.sh` completed with exit status `0` and reported that OpenAPI contracts and generated frontend DTO types are current. |
| Rebase-discovered validation fixes | PASS | Upstream graph schema fixes are now supplied by `origin/main`, and the workflow page change is minimally adapted so `pnpm check` continues to pass after the Sprint 5 evidence migration is rebased. |
| Whitespace check | PASS | `git diff --check` reported no whitespace errors. |

> Sprint 5 validation concluded with: `Contract freshness gate passed: OpenAPI contracts and generated frontend DTO types are current.` The final validation was performed after the Sprint 5 commit was amended to include the rebase fixes and regenerated contract artifacts.

## Residual Risks and Follow-Up

The evidence schemas use `.passthrough()` on response records where backend services can include additional metadata fields or where future OpenAPI response models may become stricter. This preserves compatibility with present L3 service behavior while still rejecting malformed critical fields at the frontend boundary. During rebase finalization, upstream workflow changes also required a small page compatibility fix, a deterministic Layer 4 workflow enum ordering fix, and regenerated L3/L4 contract artifacts; those changes are included only to keep the rebased Sprint 5 branch type-safe and contract-fresh. The graph schema blocker that appeared earlier in the rebase sequence is now resolved upstream on `origin/main`, not duplicated in this Sprint 5 commit.

| Follow-Up | Recommended Priority | Rationale |
|---|---:|---|
| Add automated no-new-response-cast enforcement for frontend hooks | P1 | Five sprints now provide enough migrated examples to justify a guard that prevents reintroducing `response.data as ...` trust boundaries in hook modules. |
| Tighten evidence OpenAPI response models and generated DTO specificity | P1 | The runtime schemas now document the frontend-consumed evidence shapes; backend response models should be hardened over time so generated contracts communicate the same guarantees. |
| Continue migrating remaining high-impact hook boundaries | P1 | Product, ground-truth governance, competitive intelligence, and evidence are now migrated; the next sprint should inventory remaining hook modules with response casts and prioritize the highest-traffic domain. |
| Extract shared boundary-test fixture conventions | P2 | Product, ground-truth governance, competitive intelligence, and evidence parser suites now share a consistent positive/negative structure that can be made easier to maintain. |

## Handoff Recommendation

Sprint 6 should first add an automated hook response-cast guard, then continue with the next remaining runtime-boundary migration. The guard is now practical because migrated hook modules provide concrete allowed patterns, parser-test examples, and schema-owned type-export conventions that can distinguish legitimate type aliases from unsafe transport response assertions.
