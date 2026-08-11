# Packet (e) — Publisher Runbook (exact merge order, per-PR gate status)

- **UTC:** 2026-08-11T05:30:00Z
- **Purpose:** the Publisher executes without interpretation. Every line states the PR, its current gate status, and the pre-merge check.
- **Rule:** merge only when the PR's required checks are green on its current head. Required contexts: `mandatory-security-regression`, `contract-compliance`, `prod-readiness`, `behavior-tests`, `Layer 5 - Source Contract`, `Layer 5 - Tenant Isolation Regression`, `Layer 5 - Contract Shape Regression`, `Structural Preflight`.

## Already merged (record only)

| Order | PR | Task | Merged (UTC) | Merge commit |
|---|---|---|---|---|
| 1 | #1265 | V1-CONTRACT-FIX (#1254) | 2026-08-10T22:34:12Z | `a09e67ef25ca` |
| 2 | #1266 | V1-IDENTITY-001 (#1255) | 2026-08-10T16:35:14Z | `5de56e7f23de` |
| 3 | #1268 | V1-AI-001 part 1 (#1259) | 2026-08-10T17:23:31Z | `da4c9a395af6` |
| 4 | #1272 | V1-QUEUE-001 (P0-02 DLQ) | 2026-08-11T00:10:17Z | `fe8c63a3da58` |
| 5 | #1270 | V1-CLAIMS-001 (#1264) | 2026-08-11T00:28:54Z | `440c1d3b4b45` |
| 6 | #1269 | V1-TENANCY-010 L1 (#1258) | 2026-08-11T00:46:48Z | `c3233c66ca20` |
| 7 | #1271 | V1-TENANCY-010 L2 (#1258) | 2026-08-11T00:59:24Z | `e3ace52032f8` |
| 8 | #1273 | v1 release packet tree (docs-only) | 2026-08-11T04:52:09Z | `271105941` |
| 9 | #1267 | V1-PROVISION-001 (#1256) | 2026-08-11T05:25:59Z | `1388e683e` |

**#1267 gate record (verified before merge):** all 8 required contexts SUCCESS on head `6e1d32c5328e9c89a8906d43c7a72a78a03edfdc` — Structural Preflight, contract-compliance, prod-readiness, mandatory-security-regression, behavior-tests, Layer 5 - Source Contract, Layer 5 - Tenant Isolation Regression, Layer 5 - Contract Shape Regression (verified 2026-08-11T05:27Z). Non-required failures at merge time (Docker Compose Config Contract, Supply Chain Summary, CI Tools Image Preflight) are pre-existing repo issues — see packet (g). #1256 was closed by the repo owner with the staged-fix evidence comment.

## Next actions in execution order

### Step 1 — Do NOT merge #1252 (V1-ROUTING-001, #1253)
- Blocking defects F-1/F-2 in `signoff-evidence/v1-routing-001-decomposition-review.md`; review comment posted on the PR.
- Action: author decomposes per the packet's 4-PR split (claim-type taxonomy → gateway orchestration delegation → delegation router → Meridian suite); the new PRs merge in that order after independent review.

### Step 2 — Apply workflow patches (packet g), in this order
1. `git apply signoff-evidence/gates/workflow-patches/ci-tools-preflight-uv-version.patch` — unblocks CI Tools Image Preflight + Supply Chain Summary on all PRs. Commit + push via a human-opened PR (workflow scope; CODEOWNERS platform/security approval per policy).
2. `git apply signoff-evidence/gates/workflow-patches/ai-evals-path-filter.patch` — completes #1259; after merge, close #1259 per its issue comment.
3. `v1-ci-001` stage-1 aggregation patch — ONLY after step 2 lands (the contract forbids enshrining broken gates) and after the #1252 decomposition lands. Stages 3–4 (branch-protection convergence) are human-sequenced after shadow parity.

### Step 3 — Provision staging (packet h)
- Sign `signoff-evidence/gates/staging-environment-request.md`, provision per §2, then run the evidence commands in §2.4 in order: #1257 DR → #1260 golden path → #1261 observability.

### Step 4 — Human decisions (packets a, b, c) and waivers (packet d)
- Independent of merge order; required before certification sign-off.

### Step 5 — Certification (Movement II)
- At the merged candidate SHA: `make validate-launch-contract`, `make release-baseline`, `CERTIFY_LIVE=1 make certify-release-candidate RELEASE_SHA=<sha>`, `make build-release-evidence RELEASE_SHA=<sha>`. Red-with-named-unblock is acceptable per Amendment 4; forced green is not.

### Dependabot PRs (#1238–#1251 class)
- M1 class (non-release-surface): mergeable after required checks pass, but several currently fail Governance Docs Guard (missing body fields) and PR Overlap Guard. Recommendation: batch-refresh after Step 1 to avoid merge-queue churn; do not let them interleave with Step 2's decomposition.

## One-signature approval block

```
Publisher acknowledges this runbook and executes in the order above.
Name: ______________  Role: Publisher  Date (UTC): __________
```
