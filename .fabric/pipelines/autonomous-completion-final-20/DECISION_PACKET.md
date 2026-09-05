# GATE-1 decision packet (resubmission materials)

**Not an approval.** `spec_gaps_signed_off` remains **false**.  
**Operator disposition:** DEFER (2026-09-05). GAP-0 = **block**.  
**Anchor:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**Prior evidence head:** `38db25bfd04ce345da3eac3039900ee2585a6ce7`

This packet answers the five DEFER conditions. Steps 2–6 stay halted.

## Index

| # | Ask | Artifact |
|---|---|---|
| 1 | Reconcile halt/resume; make Step 1 exception explicit | [HALT_POLICY.md](./HALT_POLICY.md), `pipeline.spec.json` `halt_and_resume`, [GATE-1.md](./GATE-1.md), [README.md](./README.md), [step_0/NOTES.md](./step_0/NOTES.md) |
| 2 | Replace “use pipeline defaults” with numeric LOC **and** file-count policy + owners | [policies/node-budget.v1.json](./policies/node-budget.v1.json) (`1.0.0-proposed`) |
| 3 | Unmet Step 0 prerequisites vs AC-20 feature work | [step_0/PREREQUISITES.md](./step_0/PREREQUISITES.md) |
| 4 | Decision table GAP-1–19 with sub-scope, lanes, owners | [step_1/DECISION_TABLE.md](./step_1/DECISION_TABLE.md) |
| 5 | Factual implementation status + recommendations only | [step_1/IMPLEMENTATION_STATUS.md](./step_1/IMPLEMENTATION_STATUS.md) |
| — | This DEFER record | [GATE-1-DISPOSITION.md](./GATE-1-DISPOSITION.md) |

## What changed in the rules (short)

- `halt_pipeline` on a red 80% **does not** stop Step 1. Step 1 is an explicit read-only exception.
- Step 2 is **not** excepted. DAG waits for GATE-1 APPROVE **and** GAP-0 not blocking.
- Your GAP-0 = **block** independently holds Steps 2–6 even if GATE-1 were later signed.
- Mapping complete ≠ gate signed. `spec_gaps_signed_off` is human-only.

## What is *not* in this packet

- No DAG (Step 2).
- No tests (Step 3).
- No application code.
- No `spec_gaps_signed_off: true`.
- No in-scope ID list filled in — the table’s last column is blank on purpose.

## What you can do next

1. Keep DEFER (default): nothing else happens.
2. Edit [DECISION_TABLE.md](./step_1/DECISION_TABLE.md) last column (in / out / other) and either approve or reject `node-budget.v1.json`.
3. When (2) is explicit **and** you write `GATE-1: APPROVE`, agents may record sign-off. Not before.

Confirmed red jobs under GAP-0 block: Runtime Contract Tests (Services Up), Integration Tests (Docker), p0-e2e-gate, plus the six Prod Readiness jobs. `02-code-quality-and-tests` was in the original snapshot but **not** in a later `failed_only` re-query — treat as unverified until a job log exists.
