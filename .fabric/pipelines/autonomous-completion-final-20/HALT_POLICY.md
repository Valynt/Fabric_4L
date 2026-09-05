# Halt and resume policy (reconciled)

**Pipeline:** `autonomous-completion-final-20` v2.0.0  
**Policy version:** `halt-policy.v1`  
**Status:** in force for this evidence branch  
**Does not authorize implementation.**

This document reconciles contradictions across `pipeline.spec.json`, Step 0 baseline, GATE-1 instructions, README, and the 2026-09-05 operator DEFER. It makes the Step 1 exception explicit.

## 1. Contradictions found (and how they are resolved)

| Source | What it said | Conflict | Resolution |
|---|---|---|---|
| `pipeline.spec.json` step_0 `failure_path.action` | `halt_pipeline` | Implies Steps 1–6 all stop | **Too broad.** Reinterpreted as halt *implementation* (Steps 3–6). Step 1 is an explicit exception. |
| Step 0 `baseline_report.json` `allowed_continuation` | Step 1 read-only mapping produced; Steps 2–6 not started | Contradicts literal `halt_pipeline` | **Canonical for Step 1.** Mapping is not “building the missing 20%.” |
| GATE-1.md / README | Step 1 complete/unsigned; Steps 2–6 not started | Same | Keep. |
| Step 1 `completion_criteria` | includes `spec_gaps_signed_off == true` | Mixes mapping done with gate signed | **Split.** Mapping artifacts can be complete while GATE-1 is unsigned. |
| Prior chat diagram | Step 2 after GATE-1 even if GAP-0 is block | Operator DEFER: GAP-0 = block | **GAP-0 block independently halts Steps 2–6** until named red jobs are green. GATE-1 sign-off alone does not resume implementation. |
| Step 0 incomplete container/metrics | `container_image_reproducible == false`, latencies null | Spec completion_criteria require a reproducible image | Step 0 stays **PARTIAL**. Does not block Step 1. **Does** block Steps 3–6 (they consume `step_0_container` and performance baselines). |

## 2. Halt classes

### H-RED-SUITE (Step 0 `failure_path`)

- **Trigger:** existing test suite red on the 80%.
- **Observed:** true on anchor `4bb4e14` (see `step_0/PREREQUISITES.md`).
- **Action:** halt **implementation** (Steps 3–6).
- **Step 1 exception (explicit):** **permitted**. Conditions: `mutations_allowed == false`, `write_access == map_artifacts_only`, purpose = produce SPEC_GAPS for human intent. Mapping is not product implementation.
- **Step 2 exception:** **not permitted.** DAG decomposition is planning-for-implementation and waits for GATE-1 **and** GAP-0 not `block` (or blocking jobs green).
- **Message:** Never build the missing 20% on a broken 80%.

### H-STEP0-INCOMPLETE

- **Trigger:** any Step 0 completion criterion unmet (reproducible container, golden baseline measurements).
- **Observed:** true (no OCI image; coverage/latency/build_time null; local suite not run).
- **Does not block:** Step 1.
- **Blocks:** Steps 3–6 until the unmet items are closed **or** the operator files a named waiver for CI-proxy baselines. A CI-proxy is not a container.

### H-GATE-1

- **Trigger:** `spec_gaps_signed_off == false` **or** disposition is DEFER / REJECT.
- **Observed:** DEFER, 2026-09-05.
- **Blocks:** Step 2 and everything after.

### H-GAP-0-BLOCK (operator, 2026-09-05)

- **Classification:** `block`.
- **Effect:** Steps 2–6 stay halted until the blocking red jobs are green. Independent of GATE-1.
- **No risk waiver** is in force.

### H-GATE-2 / H-GATE-3

Unchanged: budget overrun on a node; human deploy decision. Not reached.

## 3. Resume rules

Resume **Step 2** only when **all** are true:

1. Operator APPROVE on GATE-1 with the four required fields (`spec_gaps_signed_off: true`).
2. GAP-0 is `accepted-risk` or `waive` with named jobs **or** GAP-0 remains `block` **and** those jobs are green on a new freeze SHA.
3. Node-budget policy `policies/node-budget.v1.json` is in force (not a slogan).

Resume **Steps 3–6** only when **all** are true:

1. Step 2 complete (acyclic DAG, ownership, budgets).
2. H-RED-SUITE cleared or waived in writing.
3. H-STEP0-INCOMPLETE cleared or waived in writing (container + measurements, or named CI-proxy waiver).
4. GATE-1 still signed against the freeze SHA in use.

**Permitted now (DEFER):** correct Step 0/1 evidence only. No DAG, no tests, no application code, no `spec_gaps_signed_off: true`.

## 4. Step 1 completion vs GATE-1

| Criterion | Owner | Current |
|---|---|---|
| `repo_map_versioned` | inspection agent | true |
| `SPEC_GAPS.md` produced | inspection agent | true |
| `risk_heatmap` produced | inspection agent | true |
| Decision packet (this round) | inspection agent | produced |
| `spec_gaps_signed_off` | **human only** | **false** |

Agents complete mapping. Humans complete the gate.
