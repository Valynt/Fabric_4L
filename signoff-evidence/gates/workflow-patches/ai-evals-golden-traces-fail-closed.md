# Workflow Patch — ai-evals golden-traces fail-closed

- **UTC:** 2026-08-11T04:50:00Z
- **Patch:** `signoff-evidence/gates/workflow-patches/ai-evals-golden-traces-fail-closed.patch`
- **Target:** `.github/workflows/ai-evals-pipeline.yml` (analyze golden trace results step, ~line 417)
- **Found by:** packet (b) evidence review — `signoff-evidence/gates/live-llm-workflows.md`
- **Apply:** `git apply signoff-evidence/gates/workflow-patches/ai-evals-golden-traces-fail-closed.patch` (verified `git apply --check` exit 0 against main `e3ace52032f8c80436e46adee4fba27402ae9f31`)

## Defect

The golden-traces analysis step catches `FileNotFoundError` (no `golden-traces-results.json`) and sets `passed=true`. The preceding step only runs pytest `if [ -f tests/evals/test_golden_traces.py ]` — and that file does not exist on main — so the results file is never produced and the gate **always silently passes**. This is the exact vacuous-gate class #1254 (V1-CONTRACT-FIX) exists to eliminate: a gate that cannot fail is not a gate.

## Fix

Fail closed: when no results file exists, print the reason, set `passed=false`, and `sys.exit(1)`. One branch changed; no other behavior touched.

## Expected gate behavior change

- Before: `run-golden-traces` passes with zero executed traces (false green).
- After: `run-golden-traces` fails until `tests/evals/test_golden_traces.py` (or its configured replacement) exists and produces results. This makes the missing-suite state visible and blocks the live-LLM decision (packet b) on honest evidence rather than a silent pass.

## Sequencing

Apply alongside `ai-evals-path-filter.patch` (both touch the same workflow, disjoint hunks; verified independently). Note for the applier: once this gate fails honestly, either the golden-trace suite must be authored (V1-EVALS-001 scope) or the job's threshold policy must be revisited by the workflow owner — that follow-up is deliberately NOT in this patch.

## Verification

- `git apply --check` from repo root: PASS.
- Branch logic reviewed against the surrounding `try/except` — `sys` is already imported in the heredoc; `set_output` helper unchanged.
