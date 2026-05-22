> **STATUS: ARCHIVED** — historical audit snapshot (2026-04-28). See [docs/archive/INDEX.md](archive/INDEX.md). Current testing strategy lives in [reference/testing-strategy.md](reference/testing-strategy.md).

# Test Audit — April 28, 2026

## Scope and method

This audit was generated from repository test files under `tests/` using:

- static inventory of `test_*.py` files and `def test_*` functions
- first-introduced file date from Git (`git log --diff-filter=A --follow`)
- end-to-end execution snapshot from `pytest tests -q`

## Portfolio summary

- **Total Python test files (`test_*.py`)**: 101
- **Total discovered test functions (`def test_*`)**: 949
- **10% target volume**: `ceil(949 * 0.10) = 95` tests

## Volume by area and broad test type

| Area | Type | Test count |
|---|---:|---:|
| security | security | 342 |
| k8s | platform | 149 |
| contract | contract | 115 |
| evals | eval | 80 |
| shared | shared | 60 |
| agents | agent | 46 |
| integration | integration | 45 |
| contracts | contract | 34 |
| config | other | 27 |
| arch | architecture | 18 |
| gitops | gitops | 14 |
| state | other | 6 |
| performance | performance | 4 |
| root | other | 4 |
| tools | other | 3 |
| context | other | 2 |
| cache | other | 0 |
| e2e | e2e | 0 |

## Pass-rate snapshot (`pytest tests -q`)

Run result:

- Passed: **447**
- Failed: **197**
- Skipped: **246**
- Errors: **70**
- Total reported outcomes: **960**

Calculated rates:

- **Pass rate vs all outcomes**: `447 / 960 = 46.56%`
- **Pass rate vs executed tests only (pass+fail)**: `447 / (447+197) = 69.41%`
- **Non-executed/error share (skip+error)**: `(246+70)/960 = 32.92%`

## Date audit and oldest 10%

Oldest tests were selected by ascending **file introduction date**, accumulating test counts until at least 95 tests.

- **Oldest cohort target**: 95 tests
- **Selected oldest cohort cumulative**: 105 tests across 18 files

### Oldest cohort files (by introduction date)

1. 2026-04-13 — `tests/contract/test_l2_l3_contract.py` (4)
2. 2026-04-13 — `tests/contract/test_l4_frontend_contract.py` (10)
3. 2026-04-13 — `tests/contract/test_tool_manifests.py` (4)
4. 2026-04-13 — `tests/evals/skills/test_evaluate_formula.py` (5)
5. 2026-04-13 — `tests/evals/skills/test_semantic_search.py` (4)
6. 2026-04-14 — `tests/arch/test_tenant_architecture.py` (3)
7. 2026-04-14 — `tests/arch/test_testability_architecture.py` (14)
8. 2026-04-14 — `tests/contract/test_api_main_architecture.py` (1)
9. 2026-04-14 — `tests/contract/test_l3_formulas_contract.py` (7)
10. 2026-04-14 — `tests/contract/test_l3_graph_contract.py` (13)
11. 2026-04-14 — `tests/contract/test_l3_value_trees_contract.py` (8)
12. 2026-04-14 — `tests/contract/test_l4_workflows_contract.py` (9)
13. 2026-04-14 — `tests/integration/billing_entitlements/test_billing_entitlements_regression.py` (9)
14. 2026-04-15 — `tests/contract/test_layer3_contract.py` (0)
15. 2026-04-15 — `tests/contract/test_layer5_contract.py` (0)
16. 2026-04-15 — `tests/contracts/test_layer3_contract.py` (0)
17. 2026-04-15 — `tests/contracts/test_layer5_contract.py` (0)
18. 2026-04-15 — `tests/gitops/test_rollouts.py` (14)

## Refactor actions applied in this change set

Refactor updates were applied to representative files from the oldest cohort to improve maintainability and reduce repetition without changing test intent:

- `tests/contract/test_tool_manifests.py`
  - deterministic manifest ordering (`sorted`)
  - module-scoped manifest cache fixture
  - compact required-field assertion loop
- `tests/evals/skills/test_evaluate_formula.py`
  - module-scoped fixture for trace loading reused across all tests
- `tests/evals/skills/test_semantic_search.py`
  - module-scoped fixture for trace loading reused across all tests
- `tests/arch/test_testability_architecture.py`
  - protocol compliance checks consolidated into one parametrized test
- `tests/gitops/test_rollouts.py`
  - extracted shared YAML loader helper and reduced duplicated file I/O/try blocks
- `tests/contract/test_l2_l3_contract.py`
  - generalized payload schema validation test structure via parametrization

