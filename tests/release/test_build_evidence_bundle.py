"""Regression tests for scripts/release/build_evidence_bundle.build_manifest.

The certification step records (certification.json) carry internal fields
(log, criterion, classification) that the candidate-manifest schema forbids
(additionalProperties: false). build_manifest must project step records onto
the schema-allowed gate shape or certification crashes end-to-end.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "release"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_evidence_bundle as build_evidence_bundle_module  # noqa: E402
from models import NOT_RUN_EXIT_CODE, RunRecord, StepResult  # noqa: E402

MANIFEST_SCHEMA = json.loads(
    (REPO_ROOT / "release" / "v1" / "schemas" / "candidate-manifest.schema.json").read_text(
        encoding="utf-8"
    )
)

FAKE_SHA = "a" * 40


def _load_module():
    module_path = REPO_ROOT / "scripts" / "release" / "build_evidence_bundle.py"
    spec = importlib.util.spec_from_file_location("build_evidence_bundle_test_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _step_result(gate: str, exit_code: int, out_dir: Path) -> StepResult:
    log_path = out_dir / f"{gate}.log"
    log_path.write_text("output\n", encoding="utf-8")
    return StepResult(
        gate=gate,
        command=f"make {gate}",
        exit_code=exit_code,
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:01:00Z",
        log=str(log_path),
        criterion="critical journeys",
        classification="pass" if exit_code == 0 else "unclassified",
    )


def _write_certification(out_dir: Path, results: list[StepResult]) -> None:
    record = RunRecord(kind="candidate-certification", sha=FAKE_SHA, branch="main")
    record.results.extend(results)
    record.write(out_dir / "certification.json")


class TestBuildManifest:
    def test_manifest_built_from_step_results_validates_against_schema(
        self, tmp_path: Path
    ) -> None:
        """StepResult internal fields must not leak into the manifest gates."""
        _write_certification(tmp_path, [_step_result("03a-verify", 0, tmp_path)])

        manifest_path = build_evidence_bundle_module.build_manifest(FAKE_SHA, tmp_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        jsonschema.validate(manifest, MANIFEST_SCHEMA)
        gate = manifest["gates"][0]
        assert set(gate) <= {
            "gate",
            "command",
            "exit_code",
            "started_at",
            "finished_at",
            "log_path",
        }
        assert gate["log_path"].endswith("03a-verify.log")
        assert manifest["certification"]["status"] == "certified"

    def test_not_run_step_fails_closed_and_still_validates(self, tmp_path: Path) -> None:
        results = [
            _step_result("03a-verify", 0, tmp_path),
            _step_result("11-load-profiles", NOT_RUN_EXIT_CODE, tmp_path),
        ]
        _write_certification(tmp_path, results)

        manifest = json.loads(
            build_evidence_bundle_module.build_manifest(FAKE_SHA, tmp_path).read_text(
                encoding="utf-8"
            )
        )

        jsonschema.validate(manifest, MANIFEST_SCHEMA)
        assert manifest["certification"]["status"] == "failed"
        assert manifest["authorization"]["production_authorized"] is False

    def test_missing_certification_record_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            build_evidence_bundle_module.build_manifest(FAKE_SHA, tmp_path)

    def test_signal_terminated_gate_is_a_failure_not_certified(self, tmp_path: Path) -> None:
        """Negative exit codes (signal deaths) must never yield a certified manifest."""
        _write_certification(tmp_path, [_step_result("03a-verify", -9, tmp_path)])

        manifest = json.loads(
            build_evidence_bundle_module.build_manifest(FAKE_SHA, tmp_path).read_text(
                encoding="utf-8"
            )
        )

        jsonschema.validate(manifest, MANIFEST_SCHEMA)
        assert manifest["certification"]["status"] == "failed"

    def test_manifest_is_bound_to_certification_record_sha(self, tmp_path: Path) -> None:
        """Records produced for a different SHA must be rejected (fail closed)."""
        _write_certification(tmp_path, [_step_result("03a-verify", 0, tmp_path)])

        with pytest.raises(SystemExit, match="not candidate"):
            build_evidence_bundle_module.build_manifest("f" * 40, tmp_path)


class TestManifestSchemaAuthorization:
    def _manifest(self, tmp_path: Path) -> dict:
        _write_certification(tmp_path, [_step_result("03a-verify", 0, tmp_path)])
        manifest_path = build_evidence_bundle_module.build_manifest(FAKE_SHA, tmp_path)
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def test_production_authorization_requires_human_identity(self, tmp_path: Path) -> None:
        manifest = self._manifest(tmp_path)
        manifest["authorization"]["production_authorized"] = True

        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(manifest, MANIFEST_SCHEMA)

        manifest["authorization"]["authorized_by"] = "release-director@example"
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(manifest, MANIFEST_SCHEMA)

        manifest["authorization"]["authorized_at"] = "2026-01-01T00:00:00Z"
        jsonschema.validate(manifest, MANIFEST_SCHEMA)


class TestRiskRegisterWaiverSchema:
    SCHEMA = json.loads(
        (REPO_ROOT / "release" / "v1" / "schemas" / "risk-register.schema.json").read_text(
            encoding="utf-8"
        )
    )

    def _register(self, status: str, waiver: dict | None) -> dict:
        risk = {
            "id": "PRR-001",
            "area": "security",
            "severity": "P0",
            "owner": "release-director",
            "status": status,
            "risk": "A sufficiently long description of the risk.",
            "validation": "make verify",
            "exit_criteria": "All hostile tenant tests pass in staging.",
        }
        if waiver is not None:
            risk["waiver"] = waiver
        return {"schema_version": 1, "snapshot_date_utc": "2026-01-01", "risks": [risk]}

    def test_waived_risk_without_waiver_is_rejected(self) -> None:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(self._register("WAIVED", None), self.SCHEMA)

    def test_waiver_without_expiry_is_rejected(self) -> None:
        waiver = {"approved_by": "release-director", "reference": "DEC-042"}
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(self._register("WAIVED", waiver), self.SCHEMA)

    def test_signed_expiring_waiver_is_accepted(self) -> None:
        waiver = {
            "approved_by": "release-director",
            "reference": "DEC-042",
            "expires": "2026-12-31",
        }
        jsonschema.validate(self._register("WAIVED", waiver), self.SCHEMA)

    def test_open_risk_without_waiver_is_accepted(self) -> None:
        jsonschema.validate(self._register("OPEN", None), self.SCHEMA)


class TestBuildReleaseEvidencePacket:
    def test_writes_candidate_scoped_manifest(self, monkeypatch, tmp_path: Path) -> None:
        module = _load_module()
        candidate_sha = "b" * 40
        out_dir = tmp_path / "artifacts" / "release" / candidate_sha
        template_dir = tmp_path / "docs" / "launch"
        template_dir.mkdir(parents=True)
        (template_dir / "evidence-manifest.example.yaml").write_text(
            'release_candidate_sha: "REPLACE_WITH_COMMIT_SHA"\n',
            encoding="utf-8",
        )

        calls: list[tuple[list[str], Path]] = []

        def _run(command, cwd=None, check=None):
            calls.append((command, cwd))
            return type("CompletedProcess", (), {"stdout": ""})()

        monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(
            module,
            "RELEASE_EVIDENCE_MANIFEST_TEMPLATE",
            template_dir / "evidence-manifest.example.yaml",
        )
        monkeypatch.setattr(
            module,
            "subprocess",
            type(
                "SubprocessStub",
                (),
                {
                    "run": staticmethod(_run),
                    "CalledProcessError": __import__("subprocess").CalledProcessError,
                },
            ),
        )

        packet_dir = module.build_release_evidence_packet(candidate_sha, out_dir)

        generated_manifest = yaml.safe_load(
            (out_dir / "release-evidence-manifest.yaml").read_text(encoding="utf-8")
        )
        assert generated_manifest["release_candidate_sha"] == candidate_sha
        assert packet_dir == out_dir / "release-evidence-packet"
        assert calls == [
            (
                [
                    sys.executable,
                    str(tmp_path / "scripts" / "ci" / "generate_release_evidence_packet.py"),
                    "--manifest",
                    str(out_dir / "release-evidence-manifest.yaml"),
                    "--output-dir",
                    str(out_dir / "release-evidence-packet"),
                    "--release-sha",
                    candidate_sha,
                ],
                tmp_path,
            )
        ]

    def test_fails_closed_on_generator_error(self, monkeypatch, tmp_path: Path) -> None:
        module = _load_module()
        candidate_sha = "c" * 40
        out_dir = tmp_path / "artifacts" / "release" / candidate_sha
        template_dir = tmp_path / "docs" / "launch"
        template_dir.mkdir(parents=True)
        (template_dir / "evidence-manifest.example.yaml").write_text(
            'release_candidate_sha: "REPLACE_WITH_COMMIT_SHA"\n',
            encoding="utf-8",
        )

        def _run(command, cwd=None, check=None):
            raise module.subprocess.CalledProcessError(returncode=7, cmd=command)

        monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
        monkeypatch.setattr(
            module,
            "RELEASE_EVIDENCE_MANIFEST_TEMPLATE",
            template_dir / "evidence-manifest.example.yaml",
        )
        monkeypatch.setattr(
            module,
            "subprocess",
            type(
                "SubprocessStub",
                (),
                {
                    "run": staticmethod(_run),
                    "CalledProcessError": __import__("subprocess").CalledProcessError,
                },
            ),
        )

        with pytest.raises(SystemExit, match="release evidence packet generation failed"):
            module.build_release_evidence_packet(candidate_sha, out_dir)
