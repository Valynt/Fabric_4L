"""Regression tests for scripts/release/build_evidence_bundle.build_manifest.

The certification step records (certification.json) carry internal fields
(log, criterion, classification) that the candidate-manifest schema forbids
(additionalProperties: false). build_manifest must project step records onto
the schema-allowed gate shape or certification crashes end-to-end.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "release"
sys.path.insert(0, str(SCRIPTS_DIR))

from build_evidence_bundle import build_manifest  # noqa: E402
from models import NOT_RUN_EXIT_CODE, RunRecord, StepResult  # noqa: E402

MANIFEST_SCHEMA = json.loads(
    (REPO_ROOT / "release" / "v1" / "schemas" / "candidate-manifest.schema.json").read_text(
        encoding="utf-8"
    )
)

FAKE_SHA = "a" * 40


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

        manifest_path = build_manifest(FAKE_SHA, tmp_path)
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
            build_manifest(FAKE_SHA, tmp_path).read_text(encoding="utf-8")
        )

        jsonschema.validate(manifest, MANIFEST_SCHEMA)
        assert manifest["certification"]["status"] == "failed"
        assert manifest["authorization"]["production_authorized"] is False

    def test_missing_certification_record_fails_closed(self, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            build_manifest(FAKE_SHA, tmp_path)
