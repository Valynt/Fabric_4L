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


def test_root_test_profile_includes_imported_runtime_clients() -> None:
    requirements = (ROOT / "tests/requirements-test.txt").read_text(encoding="utf-8")
    lock = (ROOT / "tests/requirements-test.lock").read_text(encoding="utf-8")

    assert "redis>=5.0.0" in requirements
    assert "redis==" in lock
    assert "asyncpg>=0.29.0" in requirements
    assert "asyncpg==" in lock


def test_checker_rejects_missing_lock(tmp_path: Path) -> None:
    checker = _load_checker()
    requirements = tmp_path / "requirements-test.txt"
    requirements.write_text("pytest>=8.3\n", encoding="utf-8")
    assert checker.check_lock(requirements, tmp_path / "missing.lock") == 1
