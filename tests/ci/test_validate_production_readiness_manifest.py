from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "validate_production_readiness_manifest.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_production_readiness_manifest", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _suite(
    tmp_path: Path,
    *,
    name: str,
    status: str,
    returncode: int | None,
    domains: list[str],
) -> dict[str, object]:
    suite_dir = tmp_path / name
    if status != "not_run":
        suite_dir.mkdir(parents=True, exist_ok=True)
        (suite_dir / "junit.xml").write_text("<testsuite />\n", encoding="utf-8")
        (suite_dir / "summary.md").write_text(f"# {name}\n", encoding="utf-8")

    return {
        "suite": name,
        "status": status,
        "returncode": returncode,
        "command": [sys.executable, "-m", "pytest", "-v", "--tb=short", f"tests/{name}/"],
        "junit_artifact": tmp_path.joinpath(name, "junit.xml").as_posix(),
        "summary_artifact": tmp_path.joinpath(name, "summary.md").as_posix(),
        "regression_domains": domains,
        "blocking": True,
    }


def _write_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _base_manifest(tmp_path: Path) -> dict[str, object]:
    suites = [
        _suite(tmp_path, name="security", status="passed", returncode=0, domains=["security", "tenant-isolation"]),
        _suite(tmp_path, name="release", status="passed", returncode=0, domains=["operational-behavior", "architecture"]),
        _suite(tmp_path, name="billing", status="passed", returncode=0, domains=["contracts", "tenant-isolation"]),
    ]
    return {
        "schema_version": 1,
        "generated_at_utc": "2026-06-22T18:52:07Z",
        "gate": "production-readiness-gate",
        "command": "make production-readiness-gate",
        "overall_status": "passed",
        "stopped_on_failure": False,
        "artifact_dir": tmp_path.as_posix(),
        "required_regression_domains": [
            "architecture",
            "contracts",
            "operational-behavior",
            "security",
            "tenant-isolation",
        ],
        "covered_regression_domains": [
            "architecture",
            "contracts",
            "operational-behavior",
            "security",
            "tenant-isolation",
        ],
        "blocks_release_on_failure": True,
        "suites": suites,
    }


def test_valid_manifest_passes_schema_and_artifact_checks(tmp_path: Path) -> None:
    validator = load_validator_module()
    manifest_path = _write_manifest(tmp_path, _base_manifest(tmp_path))

    assert validator.validate_manifest(manifest_path) == []


def test_passed_manifest_requires_full_domain_coverage(tmp_path: Path) -> None:
    validator = load_validator_module()
    payload = _base_manifest(tmp_path)
    suites = payload["suites"]
    assert isinstance(suites, list)
    billing_suite = suites[2]
    assert isinstance(billing_suite, dict)
    billing_suite["regression_domains"] = ["tenant-isolation"]
    payload["covered_regression_domains"] = [
        "architecture",
        "operational-behavior",
        "security",
        "tenant-isolation",
    ]
    manifest_path = _write_manifest(tmp_path, payload)

    errors = validator.validate_manifest(manifest_path)

    assert "overall passed requires all required regression domains to be covered" in errors


def test_executed_suite_requires_existing_artifacts(tmp_path: Path) -> None:
    validator = load_validator_module()
    payload = _base_manifest(tmp_path)
    suites = payload["suites"]
    assert isinstance(suites, list)
    first_suite = suites[0]
    assert isinstance(first_suite, dict)
    Path(str(first_suite["junit_artifact"])).unlink()
    manifest_path = _write_manifest(tmp_path, payload)

    errors = validator.validate_manifest(manifest_path)

    assert any("junit_artifact does not exist" in error for error in errors)


def test_not_run_suite_must_be_failed_fail_fast_manifest(tmp_path: Path) -> None:
    validator = load_validator_module()
    payload = _base_manifest(tmp_path)
    suites = payload["suites"]
    assert isinstance(suites, list)
    suites.append(
        _suite(
            tmp_path,
            name="audit",
            status="not_run",
            returncode=None,
            domains=["security", "operational-behavior"],
        )
    )
    manifest_path = _write_manifest(tmp_path, payload)

    errors = validator.validate_manifest(manifest_path)

    assert "overall passed requires every suite status to be passed" in errors
