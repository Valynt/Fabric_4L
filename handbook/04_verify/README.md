# Stage 04 — Verify

Goal: prove the change against the release control model and produce evidence bound to the
exact SHA.

## Input

- The implemented change from `03_implement/`, its design note, and its behavior card.

## Procedure

1. **Map the change to release gates.** All nine aggregate gates AG-01..AG-09 are required
   check contexts; identify which are materially exercised by this change (see
   `control-plane/release/control_register.yaml` and each L2 component page's gate list):
   - AG-01 repository-integrity — structure, generated-file and policy drift.
   - AG-02 code-quality-and-tests — lint, types, unit/integration/browser tests, coverage.
   - AG-03 contract-compliance — OpenAPI/schema/client drift, compatibility.
   - AG-04 security-gates — SAST, secrets, auth checks, DAST.
   - AG-05 tenant-isolation-and-behavior — hostile cross-tenant proof.
   - AG-06 production-readiness — migrations, manifests, restore, resilience.
   - AG-07 supply-chain-integrity — SBOM, signing, provenance.
   - AG-08 release-evidence — evidence completeness, freshness, SHA binding.
   - AG-09 change-risk-and-approval — risk class, CODEOWNER/independent approval.
2. **Run the behavior card's Verification section.** Execute the tests, tenant-isolation
   assertions, and release controls (`CTRL-xx`) the card names. Fail-closed semantics: a failed,
   missing, skipped, cancelled, or stale control blocks. `not_applicable` requires a
   version-controlled rule, not a contributor's choice.
3. **Produce evidence records** per `control-plane/release/evidence_schema.json`. Every record
   binds: `source_sha`, `merge_group_sha`, `artifact_digest` (when built), `workflow_run_id`,
   conclusion, timestamps, and artifact references. Evidence MUST refer to the exact candidate —
   a later commit invalidates SHA-bound evidence.

## Output

- Evidence records conforming to `control-plane/release/evidence_schema.json`, bound to the
  change's SHA.
- A gate summary: for each AG-0x — success / blocked (with blocking control ID) / not
  applicable (with rule reference).

## Verification

- The decision algorithm is specified in `control-plane/release/evaluator.md`. The evaluator
  determines expected controls, verifies all required conclusions, checks evidence freshness,
  and emits `RELEASE_AUTHORIZED` or `BLOCKED` from the same data — do not hand-compute a
  different verdict.
- Merge authorization, release authorization, and production promotion are separate decision
  points; evidence for one does not substitute for another.

If blocked: record the blocking `CTRL-xx`, link the owning gap (`GAP-xx`) or open one, and do
not weaken the control to pass.
