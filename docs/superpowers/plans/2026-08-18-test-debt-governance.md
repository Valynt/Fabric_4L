# Canonical Test-Debt Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace duplicated test-debt controls with one fail-closed evaluator backed by the canonical skip register and emitting a deterministic remediation queue.

**Architecture:** Extend `scripts/ci/check_test_skip_governance.py` into the single static policy engine and report renderer, with `config/ci/test_skip_register.yaml` as its only human-maintained inventory. Preserve public command names through policy-free delegates, and treat pytest collection output only as optional evidence.

**Tech Stack:** Python 3.11, PyYAML, pytest, GNU Make, GitHub Actions, Markdown/JSON reports.

## Global Constraints

- Do not perform a broad test rewrite or directory reorganization.
- Preserve fail-closed behavior for unregistered, expired, malformed, duplicate, ambiguous, focused, critical-path-prohibited, and newly exposed debt.
- Static scanning is authoritative; collection/runtime data is subordinate evidence.
- Use stable violation codes and generate P0/P1/P2/VALID inventory and deterministic next-wave ranking.
- Existing command names may remain only as thin delegates with no independent policy.

---

### Task 1: Capture pre-consolidation evidence

**Files:**
- Create: `docs/governance/test-debt-governance-inventory.md`

**Interfaces:**
- Consumes: current register, legacy checker outputs, and timings.
- Produces: reproducible baseline metrics and command list for the final comparison.

- [ ] Run the current static, temporal, uniqueness, and collection controls with `/usr/bin/time`, preserving their JSON output and exit status.
- [ ] Count statically detectable marker types across the intended canonical surfaces.
- [ ] Record dated baseline measurements and explicitly distinguish passing controls from known violations or environment limitations.
- [ ] Commit the evidence document with `docs: record test-debt governance baseline`.

### Task 2: Characterize the canonical policy API

**Files:**
- Modify: `tests/ci/test_test_skip_governance.py`
- Modify: `tests/ci/test_temporal_skip_guard.py`
- Modify: `tests/ci/test_check_test_skip_register_uniqueness.py`

**Interfaces:**
- Consumes: `evaluate(root, register_path, scan_roots, today, collection_evidence=None)`.
- Produces: assertions against `report["violations"][*]["code"]`, report schema, inventory groups, and next-wave queue.

- [ ] Add complete register fixtures including remediation and disposition fields.
- [ ] Add ALLOW tests for legitimate environment limitations and permitted temporary waivers.
- [ ] Add DENY tests for every required failure mode, including service-directory bypass, temporal debt, ambiguity, stale entries, and critical-path policy.
- [ ] Add report and deterministic ranking tests.
- [ ] Run `pytest -q tests/ci/test_test_skip_governance.py` and verify the new tests fail for missing behavior.
- [ ] Commit the failing characterization suite with `test: characterize canonical test-debt governance`.

### Task 3: Implement the authoritative evaluator

**Files:**
- Modify: `scripts/ci/check_test_skip_governance.py`

**Interfaces:**
- Produces: typed `Finding`, `RegisterEntry`, and `Violation`; `evaluate(...) -> dict[str, Any]`; JSON and Markdown renderers; stable `TDG###` codes.
- Consumes: one YAML register and optional collection evidence path.

- [ ] Implement canonical test-surface discovery for `tests`, `services/**/tests`, and `apps/web/e2e`.
- [ ] Implement complete schema/semantic validation and exact-one-match reconciliation.
- [ ] Implement temporal, focused-marker, stale/orphan, and critical-path policies.
- [ ] Implement versioned JSON, Markdown, console, GitHub summary, metrics, inventory, and deterministic queue output.
- [ ] Run the characterization suite until green, then refactor while keeping it green.
- [ ] Commit with `feat: consolidate test-debt policy evaluation`.

### Task 4: Migrate canonical inventory

**Files:**
- Modify: `config/ci/test_skip_register.yaml`
- Remove: `config/ci/pytest_skip_allowlist.yaml`
- Remove: `config/ci/pytest_skip_baseline.json`
- Remove: `config/ci/temporal_skip_baseline.json`
- Remove if unreferenced: `scripts/ci/pytest_skip_allowlist.yaml`
- Remove if unreferenced: `scripts/ci/pytest_skip_baseline.json`

**Interfaces:**
- Consumes: authoritative scanner findings and legacy inventory data.
- Produces: one complete, valid register whose entries reconcile exactly once.

- [ ] Map every legacy-accepted exception to a canonical entry before deleting alternate data.
- [ ] Add disposition/remediation metadata to existing entries and register newly exposed service debt without changing test behavior.
- [ ] Classify entries as P0/P1/P2 or derived VALID and assign accountable risk-based ownership and next action.
- [ ] Run the authoritative evaluator on the repository and resolve only register/schema/reconciliation defects.
- [ ] Commit with `chore: migrate test debt to canonical register`.

### Task 5: Subordinate legacy entry points and CI wiring

**Files:**
- Modify: `scripts/ci/check_temporal_skips.py`
- Modify: `scripts/ci/check_test_skip_register_uniqueness.py`
- Modify: `scripts/ci/check_pytest_skip_governance.py`
- Modify: `Makefile`
- Modify: `.github/workflows/pr-checks.yml`
- Modify: `package.json` if output flags change.

**Interfaces:**
- Consumes: canonical evaluator CLI.
- Produces: compatibility commands that forward arguments and authoritative exit status without policy constants or inventories.

- [ ] Replace specialized checker implementations with thin delegates.
- [ ] Make collection governance invoke static governance with collection output as evidence.
- [ ] Converge Make, structural preflight, PR, and readiness callers on the canonical gate and outputs.
- [ ] Add tests proving delegates contain no independent policy and preserve exit behavior.
- [ ] Run all governance CI tests and compatibility targets.
- [ ] Commit with `ci: route test-debt checks through canonical evaluator`.

### Task 6: Generate post-change inventory and validate

**Files:**
- Modify: `docs/governance/test-debt-governance-inventory.md`
- Create: `artifacts/test-debt-governance.json` only if repository artifact policy permits tracked evidence; otherwise document the generated path and summarize it in the governance document.

**Interfaces:**
- Consumes: final evaluator and canonical register.
- Produces: before/after metrics, current P0/P1/P2/VALID inventory, and deterministic next-wave queue.

- [ ] Run the final evaluator with JSON and Markdown output and capture elapsed time.
- [ ] Run focused governance tests and every compatibility Make target.
- [ ] Run structural preflight and the broadest feasible `make verify`, recording exact environment blockers.
- [ ] Confirm no alternate human-maintained test-debt inventory remains referenced.
- [ ] Update the evidence document with post-change metrics and the first small P0 remediation wave.
- [ ] Run `git diff --check` and re-run the final focused verification commands.
- [ ] Commit with `docs: publish canonical test-debt remediation queue`.
