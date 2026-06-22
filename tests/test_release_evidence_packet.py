from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts/ci/generate_release_evidence_packet.py"
    spec = importlib.util.spec_from_file_location("generate_release_evidence_packet", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_manifest(path: Path, release_sha: str) -> None:
    path.write_text(
        "\n".join(
            [
                f'release_candidate_sha: "{release_sha}"',
                'generated_at_utc: "2026-01-01T00:00:00Z"',
                "gates:",
                "  production_like_e2e:",
                "    status: REQUIRES_ENVIRONMENT",
                "    owner: qa-owner",
                "    evidence_uri: null",
                '    acceptance: "Launch journey passes."',
                "  enterprise_sso_oidc:",
                "    status: REQUIRES_ENVIRONMENT",
                "    owner: identity-owner",
                "    evidence_uri: null",
                '    acceptance: "SSO validation complete."',
                "  rollback_restore:",
                "    status: REQUIRES_ENVIRONMENT",
                "    owner: sre-owner",
                "    evidence_uri: null",
                '    acceptance: "Rollback verified."',
                "  telemetry_alerting:",
                "    status: REQUIRES_ENVIRONMENT",
                "    owner: obs-owner",
                "    evidence_uri: null",
                '    acceptance: "Telemetry verified."',
                "  billing_metering:",
                "    status: REQUIRES_ENVIRONMENT",
                "    owner: billing-owner",
                "    evidence_uri: null",
                '    acceptance: "Billing verified."',
                "  performance_smoke:",
                "    status: REQUIRES_ENVIRONMENT",
                "    owner: perf-owner",
                "    evidence_uri: null",
                '    acceptance: "Performance smoke verified."',
                "allowed_statuses:",
                "  - REQUIRES_ENVIRONMENT",
                "  - PASS_WITH_EVIDENCE",
                "  - FAIL",
                "  - WAIVED",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _production_readiness_suite(
    root: Path,
    name: str,
    domains: list[str],
) -> dict[str, object]:
    suite_dir = root / name
    suite_dir.mkdir(parents=True, exist_ok=True)
    (suite_dir / "junit.xml").write_text("<testsuite />\n", encoding="utf-8")
    (suite_dir / "summary.md").write_text(f"# {name}\n", encoding="utf-8")
    return {
        "suite": name,
        "status": "passed",
        "returncode": 0,
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "--tb=short",
            f"tests/{name}/",
        ],
        "junit_artifact": suite_dir.joinpath("junit.xml").as_posix(),
        "summary_artifact": suite_dir.joinpath("summary.md").as_posix(),
        "regression_domains": domains,
        "blocking": True,
    }


def _write_production_readiness_manifest(path: Path, *, release_authorizing: bool = True) -> None:
    root = path.parent
    if release_authorizing:
        suites = [
            _production_readiness_suite(root, "security", ["security", "tenant-isolation"]),
            _production_readiness_suite(root, "release", ["operational-behavior", "architecture"]),
            _production_readiness_suite(root, "billing", ["contracts", "tenant-isolation"]),
        ]
        gate_scope = "full"
        covered_domains = ["architecture", "contracts", "operational-behavior", "security", "tenant-isolation"]
    else:
        suites = [
            _production_readiness_suite(root, "release", ["operational-behavior", "architecture"]),
        ]
        gate_scope = "subset"
        covered_domains = ["architecture", "operational-behavior"]

    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at_utc": "2026-06-22T18:52:07Z",
                "gate": "production-readiness-gate",
                "command": "make production-readiness-gate",
                "gate_scope": gate_scope,
                "overall_status": "passed",
                "stopped_on_failure": False,
                "artifact_dir": root.as_posix(),
                "required_regression_domains": [
                    "architecture",
                    "contracts",
                    "operational-behavior",
                    "security",
                    "tenant-isolation",
                ],
                "covered_regression_domains": covered_domains,
                "blocks_release_on_failure": True,
                "release_authorizing": release_authorizing,
                "suites": suites,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_generate_release_evidence_packet_writes_outputs(tmp_path, monkeypatch):
    module = _load_module()
    manifest_path = tmp_path / "manifest.yaml"
    production_readiness_manifest_path = tmp_path / "production-readiness" / "manifest.json"
    output_dir = tmp_path / "packet"
    release_sha = "abc123"
    _write_manifest(manifest_path, release_sha)
    _write_production_readiness_manifest(production_readiness_manifest_path)

    validator_names = []

    def fake_validate_manifest(_path: Path) -> list[str]:
        return []

    def fake_run_validator(name: str, command: list[str]):
        validator_names.append((name, command))
        return module.ValidatorResult(name=name, passed=True, command=command, detail="ok")

    monkeypatch.setattr(module, "_load_manifest_validator", lambda: fake_validate_manifest)
    monkeypatch.setattr(module, "_run_validator", fake_run_validator)

    exit_code = module.generate_release_evidence_packet(
        manifest_path=manifest_path,
        production_readiness_manifest_path=production_readiness_manifest_path,
        output_dir=output_dir,
        release_sha=release_sha,
        allow_placeholder_sha=False,
    )

    assert exit_code == 0
    assert len(validator_names) == 6
    assert validator_names[1][0] == "production_readiness_manifest"

    packet = json.loads((output_dir / "release-evidence-packet.json").read_text(encoding="utf-8"))
    assert packet["release_sha"] == release_sha
    assert packet["overall_status"] == "PASS"
    assert packet["production_readiness_gate"]["manifest_found"] is True
    assert packet["production_readiness_gate"]["gate_scope"] == "full"
    assert packet["production_readiness_gate"]["release_authorizing"] is True
    assert packet["production_readiness_gate"]["covered_regression_domains"] == [
        "architecture",
        "contracts",
        "operational-behavior",
        "security",
        "tenant-isolation",
    ]
    assert any(
        validator["name"] == "production_readiness_release_authorization" and validator["passed"] is True
        for validator in packet["validators"]
    )

    summary = (output_dir / "release-evidence-summary.md").read_text(encoding="utf-8")
    assert "Release Evidence Packet" in summary
    assert "Overall status: **PASS**" in summary
    assert "Production Readiness Gate" in summary


def test_generate_release_evidence_packet_fails_on_sha_mismatch(tmp_path):
    module = _load_module()
    manifest_path = tmp_path / "manifest.yaml"
    _write_manifest(manifest_path, "sha-in-manifest")

    with pytest.raises(ValueError, match="does not match release SHA"):
        module.generate_release_evidence_packet(
            manifest_path=manifest_path,
            production_readiness_manifest_path=tmp_path / "production-readiness" / "manifest.json",
            output_dir=tmp_path / "packet",
            release_sha="different-sha",
            allow_placeholder_sha=False,
        )


def test_generate_release_evidence_packet_returns_nonzero_when_validator_fails(tmp_path, monkeypatch):
    module = _load_module()
    manifest_path = tmp_path / "manifest.yaml"
    production_readiness_manifest_path = tmp_path / "production-readiness" / "manifest.json"
    output_dir = tmp_path / "packet"
    release_sha = "abc123"
    _write_manifest(manifest_path, release_sha)
    _write_production_readiness_manifest(production_readiness_manifest_path)

    def fake_validate_manifest(_path: Path) -> list[str]:
        return []

    def fake_run_validator(name: str, command: list[str]):
        passed = name != "platform_contract_lint"
        return module.ValidatorResult(name=name, passed=passed, command=command, detail="ok" if passed else "failed")

    monkeypatch.setattr(module, "_load_manifest_validator", lambda: fake_validate_manifest)
    monkeypatch.setattr(module, "_run_validator", fake_run_validator)

    exit_code = module.generate_release_evidence_packet(
        manifest_path=manifest_path,
        production_readiness_manifest_path=production_readiness_manifest_path,
        output_dir=output_dir,
        release_sha=release_sha,
        allow_placeholder_sha=False,
    )

    packet = json.loads((output_dir / "release-evidence-packet.json").read_text(encoding="utf-8"))
    assert exit_code == 1
    assert packet["overall_status"] == "FAIL"


def test_generate_release_evidence_packet_fails_for_subset_production_readiness_manifest(tmp_path, monkeypatch):
    module = _load_module()
    manifest_path = tmp_path / "manifest.yaml"
    production_readiness_manifest_path = tmp_path / "production-readiness" / "manifest.json"
    output_dir = tmp_path / "packet"
    release_sha = "abc123"
    _write_manifest(manifest_path, release_sha)
    _write_production_readiness_manifest(production_readiness_manifest_path, release_authorizing=False)

    def fake_validate_manifest(_path: Path) -> list[str]:
        return []

    def fake_run_validator(name: str, command: list[str]):
        return module.ValidatorResult(name=name, passed=True, command=command, detail="ok")

    monkeypatch.setattr(module, "_load_manifest_validator", lambda: fake_validate_manifest)
    monkeypatch.setattr(module, "_run_validator", fake_run_validator)

    exit_code = module.generate_release_evidence_packet(
        manifest_path=manifest_path,
        production_readiness_manifest_path=production_readiness_manifest_path,
        output_dir=output_dir,
        release_sha=release_sha,
        allow_placeholder_sha=False,
    )

    packet = json.loads((output_dir / "release-evidence-packet.json").read_text(encoding="utf-8"))
    assert exit_code == 1
    assert packet["overall_status"] == "FAIL"
    assert packet["production_readiness_gate"]["gate_scope"] == "subset"
    assert packet["production_readiness_gate"]["release_authorizing"] is False
    assert any(
        validator["name"] == "production_readiness_release_authorization" and validator["passed"] is False
        for validator in packet["validators"]
    )


def test_generate_release_evidence_packet_records_missing_production_readiness_manifest(tmp_path, monkeypatch):
    module = _load_module()
    manifest_path = tmp_path / "manifest.yaml"
    missing_production_readiness_manifest_path = tmp_path / "production-readiness" / "manifest.json"
    output_dir = tmp_path / "packet"
    release_sha = "abc123"
    _write_manifest(manifest_path, release_sha)

    def fake_validate_manifest(_path: Path) -> list[str]:
        return []

    def fake_run_validator(name: str, command: list[str]):
        passed = name != "production_readiness_manifest"
        return module.ValidatorResult(
            name=name,
            passed=passed,
            command=command,
            detail="ok" if passed else "manifest missing",
        )

    monkeypatch.setattr(module, "_load_manifest_validator", lambda: fake_validate_manifest)
    monkeypatch.setattr(module, "_run_validator", fake_run_validator)

    exit_code = module.generate_release_evidence_packet(
        manifest_path=manifest_path,
        production_readiness_manifest_path=missing_production_readiness_manifest_path,
        output_dir=output_dir,
        release_sha=release_sha,
        allow_placeholder_sha=False,
    )

    packet = json.loads((output_dir / "release-evidence-packet.json").read_text(encoding="utf-8"))
    assert exit_code == 1
    assert packet["overall_status"] == "FAIL"
    assert packet["production_readiness_gate"]["manifest_found"] is False
    assert packet["production_readiness_gate"]["overall_status"] == "missing"
