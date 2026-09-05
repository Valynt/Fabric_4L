# GATE-1 — Human review required

**Blocking:** yes  
**Disposition:** **DEFER** (2026-09-05) — see `GATE-1-DISPOSITION.md`  
**Target:** `step_1/DECISION_TABLE.md` (sign-off) + `step_1/SPEC_GAPS.md` (catalog)  
**Rule:** agents_must_not_guess_product_intent  
**`spec_gaps_signed_off`:** false

## Halt (two independent brakes)

1. **H-RED-SUITE / GAP-0 = block** (operator): Steps 2–6 halted until named red jobs are green. See `HALT_POLICY.md` and `step_0/PREREQUISITES.md`.
2. **H-GATE-1 DEFER:** Step 2 not started. Mapping may be corrected.

## Step 1 exception (explicit)

Step 0 `failure_path` originally said `halt_pipeline`. That is **too broad**.

Step 1 **may** run and **may** be corrected while the 80% is red because:

- `mutations_allowed: false`
- `write_access: map_artifacts_only`
- it does not implement the missing 20%
- GATE-1 cannot be decided without the map + this packet

Step 2 **may not** run under the same exception.

## Packet to review before any resubmission

| File | Role |
|---|---|
| `DECISION_PACKET.md` | Cover |
| `HALT_POLICY.md` | Halt/resume, Step 1 exception |
| `policies/node-budget.v1.json` | Numeric LOC + file caps + CODEOWNERS (proposed) |
| `step_0/PREREQUISITES.md` | Unmet freeze items vs feature work |
| `step_1/IMPLEMENTATION_STATUS.md` | Evidence for RFC/PR/code status |
| `step_1/DECISION_TABLE.md` | GAP-1–19 sub-scope, lanes, blank human column |

Do not set `spec_gaps_signed_off` true until the operator explicitly approves this packet.
