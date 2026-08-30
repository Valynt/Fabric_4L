# Goal: Remediate Brooks-Lint Test Quality Findings

## User Request

Remediate these findings:
- **T3 — Duplicated contract-test scaffolding across the two skip-safety suites**
- **T2b — Workflow-permission allowlist is an inference-internal hard-coded list**
- **T2a — Contract tests assert byte-exact workflow text, not semantics**

## Refined Goal

Eliminate test scaffolding duplication, decouple configuration data from test code, and improve contract assertion resilience across CI test suites. Extract a shared helper module for change-scope skip-safety tests, move workflow write permission allowlists into a version-controlled YAML configuration with bidirectional stale-entry validation, and make semantic contract assertions tolerant to harmless formatting and whitespace differences.

## Acceptance Criteria

- [ ] 1. Extract shared change-scope contract testing utilities into `tests/ci/_change_scope_contract.py` (including `parse_scope_expr`, `aggregate_step`, `skip_safe_entries`, `normalize_expr`, and `SCOPE_CLAUSE`).
- [ ] 2. Refactor `tests/ci/test_supply_chain_skip_safety.py` and `tests/ci/test_release_evidence_skip_safety.py` to consume the shared helpers without losing any test coverage or invariant assertions.
- [ ] 3. Move the hard-coded `ALLOWED_WRITE_PERMISSIONS` map out of `tests/ci/test_workflow_permissions.py` into `config/ci/workflow-write-permissions.yaml`.
- [ ] 4. Update `tests/ci/test_workflow_permissions.py` to load from `config/ci/workflow-write-permissions.yaml` and add a test verifying that no stale/unused allowlisted permissions exist.
- [ ] 5. Normalize whitespace and formatting in contract assertions in `tests/ci/` so semantic equivalence is tested rather than fragile byte-exact syntax.
- [ ] 6. All CI and test quality validation commands pass (`python -m pytest tests/ci/`, `structural_preflight.py`, `contract_compliance_gate.py`).

## Scope Boundaries

**In scope:**
- `tests/ci/_change_scope_contract.py` (new helper)
- `tests/ci/test_supply_chain_skip_safety.py`
- `tests/ci/test_release_evidence_skip_safety.py`
- `config/ci/workflow-write-permissions.yaml` (new config)
- `tests/ci/test_workflow_permissions.py`
- Relevant contract test assertion normalization

**Out of scope:**
- Workflow logic or production service changes
- Altering CI gate contracts, permission requirements, or scope filtering semantics
- Changes outside CI tests and CI configuration

## Applicable Project Conventions

**Quality gate command:**
- `python -m pytest tests/ci/`
- `python scripts/ci/structural_preflight.py --strict`
- `python scripts/ci/contract_compliance_gate.py`

**Commit convention:**
- Conventional commits: `type(scope): [B] description` for Builder, `chore(scope): [I] description` for Inspector
- Assisted-by trailer required: `Assisted-by: OpenAI:GPT-5.6 Luna` (Builder) / `Assisted-by: OpenAI:GPT-5.6 Sol` (Inspector)
