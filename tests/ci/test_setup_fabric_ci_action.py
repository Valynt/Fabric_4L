from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / ".github/actions/setup-fabric-ci/action.yml"
POC = ROOT / ".github/workflows/poc-governance-automation.yml"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_action_exposes_explicit_python_dependency_modes() -> None:
    text = _text(ACTION)
    assert "python-dependency-mode:" in text
    assert 'default: "root-test"' in text
    assert "root-test or none" in text
    assert "install-python-deps:" not in text


def test_root_test_mode_uses_hash_pinned_lock_and_checks_integrity() -> None:
    text = _text(ACTION)
    assert "inputs.python-dependency-mode == 'root-test'" in text
    assert "python -m pip install --require-hashes -r tests/requirements-test.lock" in text
    assert "python -m pip check" in text


def test_action_rejects_unsupported_dependency_modes() -> None:
    text = _text(ACTION)
    assert "root-test|none" in text
    assert "Unsupported python-dependency-mode" in text


def test_summary_records_actual_tool_versions_and_mode() -> None:
    text = _text(ACTION)
    assert 'python --version' in text
    assert 'node --version' in text
    assert 'pnpm --version' in text
    assert 'PYTHON_DEPENDENCY_MODE' in text


def test_poc_uses_canonical_root_test_mode() -> None:
    text = _text(POC)
    assert "python-dependency-mode: root-test" in text
    assert "install-python-deps:" not in text
