# CI Python Determinism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the four affected Python CI paths install deterministic prerequisites, use canonical service topology, and fail only on their intended validation assertions.

**Architecture:** Keep service environments authoritative through their checked-in `uv.lock` files, add a hash-pinned root test lock for root pytest jobs, and extend the existing `setup-fabric-ci` composite for root-test consumers. Layer 2 loads a public-only CI verification key fixture; Layer 3 OpenAPI generation runs from the service directory and imports `api.main`.

**Tech Stack:** GitHub Actions YAML, Python 3.11, uv 0.11.6, pytest, PyYAML, JSON, pnpm 10.18.1.

## Global Constraints

- Do not modify application behavior or weaken Layer 2 strict authentication.
- Do not lower lint, coverage, contract, security, or branch-protection thresholds.
- Preserve every existing service `uv.lock`; only add the root test lock intentionally.
- Use Python 3.11, uv 0.11.6, Node 22.18.0, and pnpm 10.18.1.
- Store public key material only; no private PEM block may enter the repository.
- Keep setup failures and validation failures as separate workflow steps.
- Do not modify frontend Docker, Layer 4 Ruff, coverage, route-audit, Schemathesis, or scanner behavior in this track.

---

### Task 1: Add the root Python test lock and freshness checker

**Files:**
- Create: `tests/requirements-test.lock`
- Create: `scripts/ci/check_python_test_lock.py`
- Create: `tests/ci/test_python_test_lock.py`
- Modify: `tests/supply_chain/test_lockfile_integrity.py`
- Modify: `scripts/ci/check_package_manager_policy.mjs`

**Interfaces:**
- Consumes: `tests/requirements-test.txt`, uv 0.11.6, Python 3.11.
- Produces: `tests/requirements-test.lock` and `check_lock(requirements: Path, lock: Path) -> int`.

- [ ] **Step 1: Write failing lock-policy and checker tests**

Add `tests/requirements-test.lock` to `expected_lockfiles` in `test_canonical_lockfiles_exist_and_are_enforced`. Create `tests/ci/test_python_test_lock.py`:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ci/check_python_test_lock.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_python_test_lock", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_root_test_lock_exists_and_uses_hashes() -> None:
    lock = ROOT / "tests/requirements-test.lock"
    text = lock.read_text(encoding="utf-8")
    assert "--hash=sha256:" in text
    assert "pytest==" in text
    assert "pyyaml==" in text


def test_checker_rejects_missing_lock(tmp_path: Path) -> None:
    checker = _load_checker()
    requirements = tmp_path / "requirements-test.txt"
    requirements.write_text("pytest>=8.3\n", encoding="utf-8")
    assert checker.check_lock(requirements, tmp_path / "missing.lock") == 1
```

- [ ] **Step 2: Run the tests and verify the expected failure**

Run:

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_python_test_lock.py \
  tests/supply_chain/test_lockfile_integrity.py::test_canonical_lockfiles_exist_and_are_enforced \
  -q
```

Expected: FAIL because the lock and checker do not exist and the policy does not recognize the new path.

- [ ] **Step 3: Implement the freshness checker**

Create `scripts/ci/check_python_test_lock.py`:

```python
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REQUIREMENTS = ROOT / "tests/requirements-test.txt"
DEFAULT_LOCK = ROOT / "tests/requirements-test.lock"


def compile_command(requirements: Path, output: Path) -> list[str]:
    return [
        "uv",
        "pip",
        "compile",
        str(requirements),
        "--python-version",
        "3.11",
        "--python-platform",
        "x86_64-unknown-linux-gnu",
        "--generate-hashes",
        "--custom-compile-command",
        "python scripts/ci/check_python_test_lock.py --write",
        "--output-file",
        str(output),
    ]


def write_lock(requirements: Path, lock: Path) -> int:
    completed = subprocess.run(compile_command(requirements, lock), cwd=ROOT, check=False)
    return completed.returncode


def check_lock(requirements: Path, lock: Path) -> int:
    if not requirements.is_file() or not lock.is_file():
        return 1
    with tempfile.TemporaryDirectory(prefix="fabric-python-lock-") as temp_dir:
        candidate = Path(temp_dir) / lock.name
        shutil.copy2(lock, candidate)
        completed = subprocess.run(compile_command(requirements, candidate), cwd=ROOT, check=False)
        if completed.returncode != 0:
            return completed.returncode
        return 0 if candidate.read_bytes() == lock.read_bytes() else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        return write_lock(DEFAULT_REQUIREMENTS, DEFAULT_LOCK)
    return check_lock(DEFAULT_REQUIREMENTS, DEFAULT_LOCK)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Generate the lock intentionally**

Run:

```bash
python scripts/ci/check_python_test_lock.py --write
```

Expected: `tests/requirements-test.lock` is created with exact versions and hashes. Inspect the complete diff and confirm no service `uv.lock` changed.

- [ ] **Step 5: Authorize and verify the new lock path**

Extend `LOCKFILE_PATTERN` and `ALLOWED_LOCKFILE_PATHS` in `scripts/ci/check_package_manager_policy.mjs` to recognize `requirements-test.lock`, and add the same path to the Python lock-integrity test set.

- [ ] **Step 6: Run focused tests and the checker**

Run:

```bash
python scripts/ci/check_python_test_lock.py
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_python_test_lock.py \
  tests/supply_chain/test_lockfile_integrity.py::test_canonical_lockfiles_exist_and_are_enforced \
  -q
node scripts/ci/check_package_manager_policy.mjs
```

Expected: PASS, with no lock changes after the check.

- [ ] **Step 7: Commit Task 1**

```bash
git add tests/requirements-test.lock scripts/ci/check_python_test_lock.py \
  tests/ci/test_python_test_lock.py tests/supply_chain/test_lockfile_integrity.py \
  scripts/ci/check_package_manager_policy.mjs
git commit -m "build(ci): lock root Python test dependencies"
```

---

### Task 2: Add deterministic root-test mode to the existing composite action

**Files:**
- Modify: `.github/actions/setup-fabric-ci/action.yml`
- Create: `tests/ci/test_setup_fabric_ci_action.py`
- Modify: `.github/workflows/poc-governance-automation.yml`

**Interfaces:**
- Consumes: `tests/requirements-test.lock`.
- Produces: composite input `python-dependency-mode` with values `root-test` and `none`.

- [ ] **Step 1: Write failing action contract tests**

Create `tests/ci/test_setup_fabric_ci_action.py` with assertions that the action declares `python-dependency-mode`, installs `tests/requirements-test.lock` with `--require-hashes` only in `root-test` mode, rejects unsupported values, runs `python -m pip check`, and writes actual `python --version`, `node --version`, and `pnpm --version` output to the summary.

- [ ] **Step 2: Run the tests to verify failure**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest tests/ci/test_setup_fabric_ci_action.py -q
```

Expected: FAIL because the input and pinned installation do not exist.

- [ ] **Step 3: Replace the boolean Python input with an explicit mode**

In `.github/actions/setup-fabric-ci/action.yml`, replace `install-python-deps` with:

```yaml
  python-dependency-mode:
    description: "Python dependency mode: root-test or none"
    required: false
    default: "root-test"
```

Add a validation step that exits nonzero unless the mode is `root-test` or `none`. Make installation conditional on `root-test` and run:

```bash
python -m pip install --require-hashes -r tests/requirements-test.lock
python -m pip check
```

Update the summary step to invoke each executable and record its actual version plus the selected mode.

- [ ] **Step 4: Migrate the proof-of-concept caller**

Change `install-python-deps: 'true'` to `python-dependency-mode: root-test` in `.github/workflows/poc-governance-automation.yml`.

- [ ] **Step 5: Run action contract and workflow policy tests**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_setup_fabric_ci_action.py \
  tests/ci/test_workflow_permissions.py -q
node scripts/ci/check_package_manager_policy.mjs
```

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add .github/actions/setup-fabric-ci/action.yml \
  .github/workflows/poc-governance-automation.yml \
  tests/ci/test_setup_fabric_ci_action.py
git commit -m "fix(ci): centralize pinned root Python setup"
```

---

### Task 3: Make Layer 2 CI authentication explicit and public-only

**Files:**
- Create: `config/ci/fabric_auth_test_public_keys.json`
- Modify: `.github/workflows/pr-checks.yml`
- Create: `tests/ci/test_layer2_ci_auth_contract.py`

**Interfaces:**
- Consumes: shared Fabric auth JSON schema `{kid, public_pem}`.
- Produces: `FABRIC_AUTH_PUBLIC_KEYS` in the Layer 2 job environment.

- [ ] **Step 1: Write failing workflow and secret-hygiene tests**

Create tests that load the JSON fixture, assert it contains exactly one `ci-test-only` key, parse its PEM with `cryptography`, reject `PRIVATE KEY`, and assert the Layer 2 job loads this exact fixture into `$GITHUB_ENV` before pytest.

- [ ] **Step 2: Run the tests to verify failure**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest tests/ci/test_layer2_ci_auth_contract.py -q
```

Expected: FAIL because the fixture and loader step do not exist.

- [ ] **Step 3: Generate a public-only fixture**

Create an ephemeral Ed25519 key outside the repository, export only its public PEM, serialize it to `config/ci/fabric_auth_test_public_keys.json`, and destroy the temporary private file after confirming the public fixture parses. Never stage the private file.

- [ ] **Step 4: Load the fixture before Layer 2 validation**

Add a named step after dependency installation in `layer2-checks`:

```yaml
      - name: Configure test-only Fabric auth verification key
        shell: bash
        run: |
          set -euo pipefail
          compact_keys="$(python -c 'import json; print(json.dumps(json.load(open("../../config/ci/fabric_auth_test_public_keys.json")), separators=(",", ":")))')"
          printf 'FABRIC_AUTH_PUBLIC_KEYS=%s\n' "$compact_keys" >> "$GITHUB_ENV"
          printf '%s\n' 'FABRIC_AUTH_ISSUER=fabric4l-gateway' >> "$GITHUB_ENV"
          printf '%s\n' 'FABRIC_AUTH_AUDIENCE=fabric4l-internal' >> "$GITHUB_ENV"
          printf '%s\n' 'FABRIC_AUTH_MODE=observe' >> "$GITHUB_ENV"
```

- [ ] **Step 5: Install pinned root gate dependencies additively**

Replace the Layer 2 ranged root requirements installation with:

```bash
uv pip install --require-hashes -r ../../tests/requirements-test.lock pytest-json-report
```

If `pytest-json-report` is not already in the root declaration, add it to `tests/requirements-test.txt`, regenerate the root lock through Task 1, and review that dependency diff rather than installing it outside the lock.

- [ ] **Step 6: Run static and Layer 2 auth tests**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_layer2_ci_auth_contract.py -q
cd services/layer2-extraction
uv sync --frozen --all-extras
uv pip install --require-hashes -r ../../tests/requirements-test.lock
FABRIC_AUTH_PUBLIC_KEYS="$(python -c 'import json; print(json.dumps(json.load(open("../../config/ci/fabric_auth_test_public_keys.json")), separators=(",", ":")))')" \
  FABRIC_AUTH_ISSUER=fabric4l-gateway \
  FABRIC_AUTH_AUDIENCE=fabric4l-internal \
  FABRIC_AUTH_MODE=observe \
  uv run pytest tests/test_l2_auth_enforcement.py -q
```

Expected: contract tests and Layer 2 auth tests PASS without private material.

- [ ] **Step 7: Commit Task 3**

```bash
git add config/ci/fabric_auth_test_public_keys.json \
  .github/workflows/pr-checks.yml tests/ci/test_layer2_ci_auth_contract.py \
  tests/requirements-test.txt tests/requirements-test.lock
git commit -m "fix(ci): configure public-only Layer 2 test auth"
```

---

### Task 4: Correct Layer 3 OpenAPI generation and lock its environment

**Files:**
- Modify: `.github/workflows/contract-compliance.yml`
- Create: `tests/ci/test_contract_compliance_python_setup.py`

**Interfaces:**
- Consumes: each matrix service's `uv.lock` and canonical module path.
- Produces: generated OpenAPI artifact from `api.main` for Layer 3.

- [ ] **Step 1: Write failing workflow topology tests**

Assert the Layer 3 matrix entry uses `module: api.main`, rejects `layer3_knowledge.api.main`, and runs `uv sync --frozen --all-extras` from `services/layer3-knowledge`. Assert OpenAPI generation uses `uv run python` with `src` on the import path.

- [ ] **Step 2: Run the test to verify failure**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_contract_compliance_python_setup.py -q
```

Expected: FAIL on the stale module and ad hoc pip setup.

- [ ] **Step 3: Update the matrix and service setup**

Add explicit `service_dir` and `module` fields:

```yaml
          - layer: layer3-knowledge
            service_dir: services/layer3-knowledge
            module: api.main
          - layer: layer5-ground-truth
            service_dir: services/layer5-ground-truth
            module: layer5_ground_truth.api.main
```

Install uv 0.11.6, run `uv sync --frozen --all-extras` in `${{ matrix.service_dir }}`, install the pinned root test lock additively, and generate with `uv run python`. Keep generation and upload paths matrix-driven.

- [ ] **Step 4: Reproduce Layer 3 generation locally**

```bash
cd services/layer3-knowledge
uv sync --frozen --all-extras
PYTHONPATH=src:../../packages/shared/src uv run python -c \
  'from api.main import app; schema = app.openapi(); assert schema["paths"]'
```

Expected: PASS with a non-empty path map and no generated tracked diff.

- [ ] **Step 5: Run workflow topology tests**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_contract_compliance_python_setup.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 4**

```bash
git add .github/workflows/contract-compliance.yml \
  tests/ci/test_contract_compliance_python_setup.py
git commit -m "fix(ci): generate Layer 3 OpenAPI from canonical module"
```

---

### Task 5: Migrate Contract Shape and Gate Engineering to the pinned root environment

**Files:**
- Modify: `.github/workflows/contract-compliance.yml`
- Modify: `.github/workflows/pr-checks.yml`
- Modify: `tests/ci/test_contract_compliance_python_setup.py`
- Create: `tests/ci/test_gate_engineering_workflow.py`

**Interfaces:**
- Consumes: `setup-fabric-ci` root-test mode.
- Produces: complete pytest environments before either validation command executes.

- [ ] **Step 1: Add failing tests for composite adoption**

Assert Contract Shape Regression and Gate Engineering invoke `./.github/actions/setup-fabric-ci` with `python-dependency-mode: root-test`. Assert Contract Shape contains no `pip install pytest httpx`, and Gate Engineering contains no `pip install jsonschema pyyaml`. Assert Gate Engineering still installs frozen pnpm dependencies and runs both existing package scripts.

- [ ] **Step 2: Run the tests to verify failure**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_contract_compliance_python_setup.py \
  tests/ci/test_gate_engineering_workflow.py -q
```

Expected: FAIL because both jobs still use incomplete package lists.

- [ ] **Step 3: Adopt the composite in both jobs**

Contract Shape uses root-test mode with `install-node-deps: 'false'` and `cache: ''`. Gate Engineering uses root-test mode with frozen Node dependencies enabled. Remove redundant setup-python, setup-node, pnpm setup, and ad hoc pip steps only within those two jobs.

- [ ] **Step 4: Reproduce the intended commands locally**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/contract/test_api_shape_regression.py -q
services/layer3-knowledge/.venv/bin/python \
  scripts/ci/gate_engineering_validator.py validate --strict
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_gate_engineering.py -q
```

Expected: all commands PASS or expose a genuine assertion defect after dependency setup; any latter failure is classified and handled separately, not hidden with another dependency patch.

- [ ] **Step 5: Run workflow contract tests**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_contract_compliance_python_setup.py \
  tests/ci/test_gate_engineering_workflow.py \
  tests/ci/test_setup_fabric_ci_action.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add .github/workflows/contract-compliance.yml .github/workflows/pr-checks.yml \
  tests/ci/test_contract_compliance_python_setup.py \
  tests/ci/test_gate_engineering_workflow.py
git commit -m "fix(ci): provision complete Python gate environments"
```

---

### Task 6: Validate the complete Track 1 change and integrate it

**Files:**
- Modify only if validation reveals a Track 1 root cause: files already listed above.
- Do not absorb unrelated baseline failures.

**Interfaces:**
- Consumes: all Task 1-5 outputs.
- Produces: reviewed branch, CI evidence, and integration into current `main`.

- [ ] **Step 1: Run the complete static contract suite**

```bash
services/layer3-knowledge/.venv/bin/python -m pytest \
  tests/ci/test_python_test_lock.py \
  tests/ci/test_setup_fabric_ci_action.py \
  tests/ci/test_layer2_ci_auth_contract.py \
  tests/ci/test_contract_compliance_python_setup.py \
  tests/ci/test_gate_engineering_workflow.py \
  tests/supply_chain/test_lockfile_integrity.py -q
```

Expected: PASS with zero skips or xfails.

- [ ] **Step 2: Run package, lock, and workflow governance checks**

```bash
python scripts/ci/check_python_test_lock.py
node scripts/ci/check_package_manager_policy.mjs
python scripts/ci/check_workflow_targets_and_artifacts.py
python scripts/ci/verify_workflow_registry.py
git diff --check main...HEAD
```

Expected: PASS. If workflow registry artifacts require regeneration, use the documented generator and include only deterministic registry changes.

- [ ] **Step 3: Run the four authoritative reproductions**

Run Contract Shape Regression, Gate Engineering, Layer 2 auth collection/subset, and Layer 3 OpenAPI import/generation exactly as specified in Tasks 3-5. Record exit codes and test counts.

- [ ] **Step 4: Audit the diff**

```bash
git status --short --branch
git diff --stat main...HEAD
git diff --name-status main...HEAD
git diff --exit-code -- services/*/uv.lock pnpm-lock.yaml apps/web/pnpm-lock.yaml
```

Expected: only the intentional root lock, workflow/action, CI fixture, tests, scripts, and documentation changes are present.

- [ ] **Step 5: Request code review and correct only Track 1 findings**

Use the repository code-review workflow. Re-run every affected test after review corrections.

- [ ] **Step 6: Publish the branch and open a focused PR**

Push `fix/ci-python-determinism`, create a PR with baseline failure links and local validation evidence, and observe the four affected root jobs before aggregate gates.

- [ ] **Step 7: Integrate and verify current main**

After required review and checks, merge the PR through the repository's normal protected-branch process. Fetch `origin/main`, fast-forward local `main`, and verify the merge commit contains every Track 1 commit:

```bash
git fetch origin main
git merge-base --is-ancestor fix/ci-python-determinism origin/main
git switch main
git merge --ff-only origin/main
git status --short --branch
```

Expected: ancestor check exits 0; local `main` equals `origin/main`; working tree is clean except separately preserved user-owned agent-memory files.
