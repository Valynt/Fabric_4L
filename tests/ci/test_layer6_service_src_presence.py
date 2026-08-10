from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER6_SRC = REPO_ROOT / "services" / "layer6-benchmarks" / "src"
REQUIRED_WRAPPERS = [
    LAYER6_SRC / "__init__.py",
    LAYER6_SRC / "api" / "__init__.py",
    LAYER6_SRC / "api" / "main.py",
    LAYER6_SRC / "api" / "deps.py",
    LAYER6_SRC / "api" / "schemas.py",
    LAYER6_SRC / "api" / "routes" / "__init__.py",
    LAYER6_SRC / "api" / "routes" / "benchmarks.py",
    LAYER6_SRC / "api" / "routes" / "system.py",
    LAYER6_SRC / "database.py",
    LAYER6_SRC / "shared_bootstrap.py",
]


def test_layer6_service_src_directory_exists() -> None:
    assert LAYER6_SRC.is_dir(), f"Missing required Layer 6 service source directory: {LAYER6_SRC}"


def test_layer6_service_entrypoint_exists() -> None:
    entrypoint = LAYER6_SRC / "api" / "main.py"
    assert entrypoint.is_file(), f"Missing Layer 6 API entrypoint required by Docker CMD: {entrypoint}"


def test_layer6_service_required_wrapper_files_exist() -> None:
    missing = [path for path in REQUIRED_WRAPPERS if not path.is_file()]
    assert not missing, "Missing required Layer 6 service wrapper files:\n" + "\n".join(str(path) for path in missing)


def test_layer6_service_tests_do_not_need_sys_path_hacks() -> None:
    pyproject = (REPO_ROOT / "services" / "layer6-benchmarks" / "pyproject.toml").read_text(encoding="utf-8")
    conftest = (REPO_ROOT / "services" / "layer6-benchmarks" / "tests" / "conftest.py").read_text(encoding="utf-8")

    assert 'pythonpath = [".", "src", "../..", "../../packages/shared/src"]' in pyproject
    assert "sys.path.insert" not in conftest


def test_layer6_service_src_main_import_resolves_from_repo_root() -> None:
    service_root = REPO_ROOT / "services" / "layer6-benchmarks"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "tests/test_api_wrapper_startup_regression.py",
            "-q",
        ],
        cwd=service_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
