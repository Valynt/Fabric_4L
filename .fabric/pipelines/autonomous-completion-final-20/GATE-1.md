# GATE-1 — Human review required

**Blocking:** yes  
**Disposition:** **DEFER** (second review, 2026-09-05) — see `GATE-1-DISPOSITION.md`  
**Target:** `step_1/DECISION_TABLE.md` (sign-off) + `step_1/GAP-3.md` + `step_1/SPEC_GAPS.md`  
**Rule:** agents_must_not_guess_product_intent  
**`spec_gaps_signed_off`:** false

A future APPROVE is valid only if it names:

1. `freeze_sha`
2. `reviewed_evidence_sha` (the packet head actually reviewed)
3. in-scope and out-of-scope IDs
4. budget policy version, or an explicit rejection of the proposed file

Later packet heads do **not** inherit sign-off.

## Halt (independent brakes; all in force)

1. **H-RED-SUITE / GAP-0 = block**
2. **H-STEP0-INCOMPLETE** (blocks Step 2; no Step 2 exception without explicit approval)
3. **H-GATE-1 DEFER**

## Step 1 exception (explicit; only exception)

Step 1 **may** be corrected while the 80% is red and Step 0 is incomplete because:

- `mutations_allowed: false`
- `write_access: map_artifacts_only` + evidence corrections
- operator DEFER text permits Step 0/1 evidence corrections

Step 2 **may not** run under that exception, including when Step 0 is incomplete.

## Packet to review

| File | Role |
|---|---|
| `DECISION_PACKET.md` | Cover |
| `HALT_POLICY.md` | Halt/resume v1.1 |
| `policies/node-budget.v1.json` | 1.1.0-proposed (add+del, freeze SHA, aggregate, generated verify) |
| `step_0/ci_inventory.json` | 45/45 + 16/16, aggregates vs causes |
| `step_0/PREREQUISITES.md` | Unmet freeze items vs feature work |
| `step_1/GAP-3.md` | Scenario route exists; schema / tenant / zeros |
| `step_1/IMPLEMENTATION_STATUS.md` | Cited status only |
| `step_1/DECISION_TABLE.md` | GAP-1–19 sub-scope, work_class, blank human column |

Do not set `spec_gaps_signed_off` true until the operator explicitly approves this packet against named SHAs.
