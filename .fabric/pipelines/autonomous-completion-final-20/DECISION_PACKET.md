# GATE-1 decision packet (resubmission materials)

**Not an approval.** `spec_gaps_signed_off` remains **false**.  
**Operator disposition:** DEFER (second review, 2026-09-05). GAP-0 = **block**.  
**Anchor / freeze:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**Reviewed and rejected as not decision-ready:** `94bfd7ebf6bed8556d39ffb5906fc7c25a68a480`

This packet answers the five corrections in the second DEFER. Steps 2–6 stay halted. No product scope, budget policy, waiver, issue closure, merge, implementation, or deployment is granted.

## Index

| # | Ask | Artifact |
|---|---|---|
| 1 | Complete paginated CI inventory; cancelled coverage; aggregates vs causes | [step_0/ci_inventory.json](./step_0/ci_inventory.json), [step_0/PREREQUISITES.md](./step_0/PREREQUISITES.md) |
| 2 | Rewrite GAP-3 (route exists; no duplicate endpoint) | [step_1/GAP-3.md](./step_1/GAP-3.md) |
| 3 | Budget policy = pipeline.spec.json (add+del, comparison SHA, aggregate, generated verify, one hard rule) | [policies/node-budget.v1.json](./policies/node-budget.v1.json) `1.1.0-proposed`, `pipeline.spec.json` |
| 4 | Resume predicates; no Step 2 exception to incomplete Step 0; sign-off bound to freeze + evidence SHA | [HALT_POLICY.md](./HALT_POLICY.md), [policies/halt_and_resume.v1.json](./policies/halt_and_resume.v1.json) `1.1.0` |
| 5 | Cited decisions only; separate external impl ownership / blocking prereqs / release requirements | [step_1/DECISION_TABLE.md](./step_1/DECISION_TABLE.md), [step_1/IMPLEMENTATION_STATUS.md](./step_1/IMPLEMENTATION_STATUS.md) |
| — | This DEFER record | [GATE-1-DISPOSITION.md](./GATE-1-DISPOSITION.md) |

## What changed vs the rejected head `94bfd7e`

- CI: 45/45 jobs, pages 1 and 2. Frontend Docker, Unified Readiness Gate, and `02-code-quality-and-tests` restored. Layer 3 **cancelled** kept. Aggregates named as aggregates.
- GAP-3: endpoint **registered and implemented**. Packet now assesses schema divergence, tenant resolution, and zero-value fallback. No second path proposed.
- Budget: `loc_delta = additions + deletions` vs freeze SHA; generated output still counts and must reproduce; aggregate caps proposed; one overrun action (`halt_node_and_flag_GATE-2`) in spec + policy.
- Halt: H-STEP0-INCOMPLETE blocks Step 2. No Step 2 exception without explicit approval (none in force). Future APPROVE must name `freeze_sha` and `reviewed_evidence_sha`.
- Governance: open council issues stay open. Unsigned SSO note is not treated as a decision. External PRs stay `external_impl_owner`. Release rows stay `release_requirement`.

## What is *not* in this packet

- No DAG (Step 2).
- No tests, no application code, no issue close, no merge.
- No `spec_gaps_signed_off: true`.
- Human-choice column still blank.

## What you can do next

1. Keep DEFER (default): nothing else happens.
2. Fill [DECISION_TABLE.md](./step_1/DECISION_TABLE.md) last column and, if you want a budget, name `node-budget.v1.json` version `1.1.0-proposed` or a superseding file.
3. When (2) is explicit **and** you write `GATE-1: APPROVE` naming this freeze SHA and the evidence SHA you reviewed, agents may record sign-off **bound to those SHAs**. Not before.
