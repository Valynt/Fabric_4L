# Layer Quality Attention Records

This record governs current file-level attention findings consumed by `scripts/ci/layer_quality_scorecard.py`.

## Ungoverned Hotspots

`packages/platform-contract/src/typescript/generated/layer4_agents.ts` and `apps/web/src/api/generated/l4/index.ts` are generated from `contracts/openapi/layer4-agents.json`. Their governing decision is contract-first ownership through OpenAPI plus API type drift validation. Direct edits to generated TypeScript remain prohibited.

`services/layer3-knowledge/src/api/models.py` remains a governed Layer 3 service-local API model exception. Ownership stays with Layer 3 Knowledge, with compatibility and contract drift handled through the service-local API and OpenAPI evidence.

## Alert Tuning Decisions

`DatabasePoolExhausted` remains critical at greater than 95 percent utilization for 2 minutes. This catches imminent connection exhaustion before query failures cascade and is paired with `docs/operations/runbooks/database-pool-exhaustion.md`.

`CriticalLLMCost` remains critical when `llm_cost_total` increases by more than $100 over 1 hour for 5 minutes. This maps to the daily budget guardrail described in the production alert rationale and the LLM cost runbooks.

`PodCrashLooping` remains critical at 3 or more restarts over 15 minutes for 5 minutes. This filters one-off restart noise while preserving detection of real crashloop behavior.

These alert decisions were refreshed on 2026-06-21 and must be reviewed by 2026-09-30.

## Knowledge Silo Remediation

`.agent/harness/conductor.py` remains owned by Brian with `@platform-agent-runtime` assigned as secondary owner for review and continuity.

The reported `.agent/harness/hooks/init.py` path is normalized to `.agent/harness/hooks/__init__.py` because `init.py` does not exist in the current checkout. Ownership remains Brian with `@platform-agent-runtime` as secondary owner.
