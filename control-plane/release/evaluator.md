# Release Evaluator — Decision Algorithm

This document is the precise specification of the RELEASE/BLOCK decision. The target
reference implementation is **`scripts/ci/evaluate_release_controls.py`** — one canonical
script that MUST: determine expected controls; verify all required conclusions; normalize
GitHub check results; validate evidence freshness; detect duplicate or missing controls;
reject unregistered critical risks; produce all aggregate conclusions; and generate the
readiness report from the same data.

The evaluator MUST fail closed. Any ambiguity, parse failure, or unverifiable input is a
BLOCK, never a pass.

## Inputs

1. **Control register** — `control-plane/release/control_register.yaml` (version 1). The
   sole source of expected controls, their decision points, and their evidence types.
2. **Evidence records** — the set of records in the certification ledger. Every record MUST
   validate against `control-plane/release/evidence_schema.json`; a record that fails
   schema validation is treated as **missing evidence**.
3. **Candidate identity** — the exact `source_sha` (40-hex), optional `merge_group_sha`,
   and the `artifact_digest` (`sha256:…`, required for release and promotion decisions).

## Normalization

- GitHub check-run conclusions are normalized into the register's conclusion space.
  `failure`, `cancelled`, `timed_out`, `action_required`, `stale`, `neutral`, and `skipped`
  check conclusions all map to blocking conclusions.
- Evidence conclusions map directly: only `pass` satisfies a control. `fail`, `cancelled`,
  `skipped`, `missing`, `stale`, and `inconclusive` block.
- `not_applicable` satisfies a control **only** when all of the following hold (register
  `not_applicable_policy`):
  1. applicability was determined by a version-controlled rule;
  2. the reason is emitted as evidence (`not_applicable_justification` in the record);
  3. the aggregate verifies the rule was evaluated;
  4. the applicability was not manually selected by a contributor.
  Path filtering MAY reduce execution but MUST never cause a required check to disappear.

## Aggregation rules

For each decision point D, let `required(D)` be every control in the register whose
`blocks` value is at or before D (`merge` ⊆ `release` ⊆ `promotion`).

For every control C in `required(D)`, the evaluator MUST verify:

1. **Existence** — at least one schema-valid evidence record exists for C. Absence →
   `missing_evidence` → BLOCK.
2. **Uniqueness** — duplicate or conflicting current records for C → BLOCK; unregistered
   control results (especially for critical risks) → BLOCK.
3. **Subject binding** — the record's `source_sha` equals the candidate `source_sha`;
   where the control's evidence type binds to the artifact, `artifact_digest` equals the
   candidate digest. Mismatch → `sha_mismatch` / `artifact_digest_mismatch` → BLOCK. A
   later commit invalidates SHA-bound evidence; rebuilding an artifact invalidates
   digest-bound certification.
4. **Freshness** — `completed_at` ≤ now ≤ `expires_at`; during certification, evidence
   MUST be no more than **24 hours** old; scheduled evidence MUST remain within its defined
   validity period. Violation → `stale` / `expired_evidence` → BLOCK.
5. **Conclusion** — `pass`, or rule-justified `not_applicable`. Anything else → BLOCK.
6. **Zero-test rule** — a critical suite MUST NOT pass with zero tests collected
   (`executed_test_count ≥ 1` and `failed == 0` for a pass).

**Aggregate semantics (fail-closed):** an aggregate gate AG-0x reports success only when
every expected required child reports success. All nine aggregates are required check
contexts on pull requests and merge groups.

**Scheduled tests:** the latest required scheduled test failing, exceeding its freshness
window, targeting an incompatible subject, not running, or being unverifiable MUST cause
AG-08 to block the next release (CTRL-08-07).

## The three decisions

| Decision | Required control subset | Subject binding |
|---|---|---|
| **Merge authorization** | All controls with `blocks: merge` (AG-01..AG-09 merge subsets) | candidate `source_sha` and, in the merge queue, the actual `merge_group_sha` |
| **Release authorization** | All controls with `blocks: merge` **or** `blocks: release`, plus AG-08 evidence verification | exact candidate `source_sha` **and** `artifact_digest` |
| **Production promotion** | All controls with `blocks: merge`, `release`, **or** `promotion`; staging certification complete; change approval bound to the final SHA | the **same signed artifact digest** certified in staging; no other artifact may deploy |

## Pseudocode

```python
BLOCKING = {"fail", "cancelled", "skipped", "missing", "stale", "inconclusive"}
FRESHNESS_CAP = timedelta(hours=24)  # during certification

def evaluate(register, ledger, candidate, decision_point) -> Decision:
    # decision_point in {merge_authorization, release_authorization, production_promotion}
    required = [c for g in register.gates for c in g.controls
                if RANK[c.blocks] <= RANK[decision_point.blocks_rank]]
    verdicts = {}
    for control in required:
        records = valid_records(ledger, control.id)   # schema-valid only; else missing
        verdicts[control.id] = evaluate_control(control, records, candidate)
    # fail-closed aggregation: gate succeeds iff every required child succeeds
    gate_results = {g.id: all(verdicts[c.id].ok for c in g.controls
                              if c in required) for g in register.gates}
    decision = "RELEASE" if all(v.ok for v in verdicts.values()) else "BLOCK"
    return Decision(decision, verdicts, gate_results)   # readiness report from same data

def evaluate_control(control, records, candidate) -> Verdict:
    if not records:
        return BLOCK("missing_evidence")
    if has_conflicting_current(records):
        return BLOCK("conflicting_evidence")
    rec = latest(records)
    if rec.source_sha != candidate.source_sha:
        return BLOCK("sha_mismatch")                    # later commit invalidates
    if binds_artifact(control) and rec.artifact_digest != candidate.artifact_digest:
        return BLOCK("artifact_digest_mismatch")        # rebuild invalidates
    if now() > rec.expires_at or now() - rec.completed_at > FRESHNESS_CAP:
        return BLOCK("expired_evidence")                # stale scheduled evidence blocks
    if rec.conclusion == "not_applicable":
        return PASS_IF(verified_versioned_rule(rec.not_applicable_justification),
                       else_=BLOCK("unjustified_not_applicable"))
    if rec.conclusion in BLOCKING or rec.conclusion != "pass":
        return BLOCK(rec.conclusion)
    if rec.failed != 0 or rec.executed_test_count == 0:
        return BLOCK("zero_test_or_failed_pass")        # zero-test rule
    return PASS()
```

## Outputs

- The decision (`RELEASE` or `BLOCK`) per decision point.
- All nine aggregate conclusions, derived from the same verdict data.
- A readiness report generated from the **same** authoritative evidence — never inferred.
  Missing or stale evidence is shown as blocked/unknown, never as passing.

## Security audit interplay

The 14 `FAB4L-SEC-*` controls (register `security_controls`) are assessed under the
Enterprise Security Audit Contract. Their audit release gates apply by priority:
GATE-DEPLOY blocks P0 (waivers prohibited); GATE-GA covers P0+P1
(`block_without_approved_plan`); GATE-P2-DEADLINE covers P2 (`open_timed_remediation`);
GATE-GOVERNANCE covers P3 (`open_backlog_item`). A repository-only assessment MUST NOT
mark a runtime-dependent check `pass`; it remains `not_assessed` until bound to a named
environment, deployed commit or image digest, and observation time. Confirmed active
secrets, cross-tenant access, remote code execution, or CI trust-boundary compromise are
immediate P0 failures and block every decision point.
