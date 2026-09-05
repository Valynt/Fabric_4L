# Halt and resume policy (reconciled, v1.1)

**Pipeline:** `autonomous-completion-final-20` v2.0.0  
**Policy:** `ac20-halt-and-resume` v1.1.0 (JSON: `policies/halt_and_resume.v1.json`)
**Status:** in force for this evidence branch  
**Does not authorize implementation, scope, waivers, or GATE-1 sign-off.**

This document reconciles `pipeline.spec.json`, Step 0 baseline, GATE-1 instructions, README, operator DEFER (first), and operator DEFER (second, reviewed head `94bfd7e`).

## 1. Contradictions found (and how they are resolved)

| Source | What it said | Conflict | Resolution |
|---|---|---|---|
| Original operator spec `step_0.failure_path.action` | `halt_pipeline` | Too broad vs mapping | Current spec action is `halt_implementation_steps_2_to_6`. Step 1 is the only exception. |
| halt-policy v1.0 `step_0_incomplete.blocks` | `[step_3..step_6]`, `does_not_block: [step_1]` | Left Step 2 unmentioned → implicit Step 2 exception to incomplete Step 0 | **Removed.** Operator (second DEFER): do not introduce a Step 2 exception to incomplete Step 0 without explicit approval. None is in force. H-STEP0-INCOMPLETE **blocks Step 2**. |
| halt-policy v1.0 `resume_step_2` | GATE-1 + GAP-0 + budget; no Step 0 complete | Same implicit exception | Resume Step 2 also requires H-STEP0-INCOMPLETE cleared, waived, or an explicit Step-2-exception approval. |
| GATE-1 sign-off | `spec_gaps_signed_off == true` with no SHA binding | A later packet could inherit an earlier approval | **Bind** APPROVE to `freeze_sha` + `reviewed_evidence_sha`. Later heads do not inherit. |
| Step 1 `completion_criteria` | included `spec_gaps_signed_off` | Mixes mapping done with gate signed | Split. Mapping can be complete while GATE-1 is unsigned. |

## 2. Halt classes

### H-RED-SUITE

- **Trigger:** existing test suite red on the freeze SHA.
- **Observed:** true. Full inventory: `step_0/ci_inventory.json` (45/45 PR Checks jobs; cancelled included).
- **Blocks:** Steps 2–6.
- **Step 1 exception:** permitted (read-only mapping / evidence correction).
- **Step 2 exception:** **not permitted.**

### H-STEP0-INCOMPLETE

- **Trigger:** reproducible container unmet, golden measurements null, or schema/seed snapshot missing.
- **Observed:** true (`container_image_reproducible == false`; p50/p95/coverage/build_time null; schema/seed snapshot not taken).
- **Blocks:** Steps 2–6.
- **Does not block:** Step 1.
- **Step 2 exception:** **not permitted** unless the operator files an explicit Step-2-exception approval. **None is in force.**

### H-GATE-1

- **Trigger:** `spec_gaps_signed_off == false` or disposition DEFER/REJECT.
- **Observed:** DEFER (second).
- **Blocks:** Step 2 and everything after.

### H-GAP-0-BLOCK (operator, 2026-09-05, still in force)

- **Classification:** `block`.
- **Effect:** Steps 2–6 halted independently of GATE-1.
- **No risk waiver** is in force.
- Blocking set uses the **full paginated inventory**, not a `failed_only` subset. Aggregates are not extra independent failures; they do not shrink the underlying set.

### H-GATE-2 / H-GATE-3

Unchanged: budget overrun; human deploy decision. Not reached.

## 3. Resume predicates (all must be true)

### Resume Step 2

1. Operator **GATE-1: APPROVE** with required fields, **bound** to a freeze SHA and a reviewed evidence SHA.
2. GAP-0 is not `block`, **or** the named **underlying** blocking jobs are green on a freeze SHA that **matches** that bound approval.
3. H-STEP0-INCOMPLETE is cleared, **or** a named waiver exists, **or** an explicit Step-2-exception approval exists. **None of those exist today.**
4. Node-budget policy version named in the bound approval is in force.

A freeze SHA change invalidates the bound APPROVE.

### Resume Steps 3–6

1. Step 2 complete against the bound freeze SHA.
2. H-RED-SUITE cleared or waived in writing.
3. H-STEP0-INCOMPLETE cleared or waived in writing (container + measurements, or named CI-proxy waiver).
4. GATE-1 still bound to the freeze SHA in use.

**Permitted now (DEFER):** correct Step 0/1 evidence only.

## 4. Sign-off freeze

A future APPROVE is valid **only** for:

- `freeze_sha`
- `reviewed_evidence_sha`
- the human-choice column of `DECISION_TABLE.md` at that SHA
- the named `node-budget` version

Changing any of those requires a new APPROVE. Agents must not treat a later packet head as signed because an earlier one was.
