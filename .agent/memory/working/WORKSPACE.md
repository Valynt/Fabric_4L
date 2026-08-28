# Workspace (live task state)

## Current task
- R3 remediation: duplicate integration clients between `services/api/app/clients/` and `layer4_agents/integration/`.
- This branch (r3/l2-client-consolidation) = gateway-side Layer 2 consolidation slice. COMPLETE.

## Done this branch
- Shared `Layer2Transport` in `packages/shared/src/value_fabric/shared/clients/layer2.py` (canonical endpoint literals, tenant/service-auth headers, timeout, HTTP boundary).
- Gateway `Layer2Client` + `layer_proxy` migrated onto it; canonical ExtractRequest payload; status path fixed; dead `list_extractions` removed.
- Tests: shared transport (5), endpoint-drift guard (4), gateway adapter (4), routing precedence (7). All pass. ruff clean.
- Committed ca31db042; PR #1549 open. Base ae8098cf9 (main).
- CI-driven fixes committed on top: 4c4fe59e4 (removed `Any` type escapes from new client files to clear check-type-escape-ratchet) and 729d7275c (relocated transport + drift-guard tests from `src/.../clients/tests/` into `packages/shared/tests/clients/` so the CI "Shared & Tests" job actually collects them; drift guard now walks up to `contracts/openapi` for repo root).
- PR #1549 body updated with required governance + incremental-gate sections; Governance Docs Guard now passes.

## Remaining R3 slices (partitioned, do NOT merge together)
- Agent-family L2 + L5 client migration onto shared transport (fresh branch from main, after #1549/#1548 land).
- Agent-client auth gap (api_key never populated) — separate P1 security PR.
- Final R3 closure report + disposition (blocked on above; currently PARTIALLY RESOLVED).
