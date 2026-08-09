"""Behavior tests for scripts/release/steps.run_step.

The certification harness must fail closed: unimplemented release operations
always block certification, and signal-terminated gate processes are recorded
as failures — never as passed or not-run.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "release"))

from models import NOT_RUN_EXIT_CODE, Step  # noqa: E402
from steps import CERTIFICATION_STEPS, run_step  # noqa: E402


class TestRunStep:
    def test_unimplemented_step_blocks_even_in_live_mode(self, tmp_path: Path) -> None:
        step = Step(
            name="05-sbom-provenance",
            command=("make", "generate-sbom-and-provenance"),
            criterion="release evidence",
            unimplemented=True,
        )

        result = run_step(step, tmp_path, live=True)

        assert result.exit_code == NOT_RUN_EXIT_CODE
        assert result.classification == "unimplemented"
        assert not result.passed
        assert "unimplemented" in (tmp_path / "05-sbom-provenance.log").read_text(
            encoding="utf-8"
        )

    def test_signal_terminated_process_is_recorded_as_failure(self, tmp_path: Path) -> None:
        step = Step(
            name="signal-death",
            command=("bash", "-c", "kill -9 $$"),
            criterion="test",
        )

        result = run_step(step, tmp_path, live=True)

        assert result.exit_code == 137  # 128 + SIGKILL
        assert result.exit_code != NOT_RUN_EXIT_CODE
        assert not result.passed
        assert not result.not_run
        assert result.classification == "unclassified"

    def test_sighup_death_cannot_collide_with_not_run_sentinel(self, tmp_path: Path) -> None:
        step = Step(
            name="sighup-death",
            command=("bash", "-c", "kill -1 $$"),
            criterion="test",
        )

        result = run_step(step, tmp_path, live=True)

        assert result.exit_code == 129  # 128 + SIGHUP, never the -1 sentinel
        assert not result.not_run
        assert not result.passed


class TestCertificationStepRegistry:
    def test_contract_required_gates_are_present(self) -> None:
        """launch-contract.yaml harness gates must appear in certification."""
        commands = {" ".join(s.command) for s in CERTIFICATION_STEPS}
        for required in (
            "make check-behavior-contract",
            "make check-behavior-readiness-audit",
            "make db-production-readiness-gate",
            "make test-backend-integrated-release-smoke",
        ):
            assert required in commands, f"certification omits contract gate: {required}"

    def test_sbom_provenance_is_not_substituted_by_a_nearby_check(self) -> None:
        sbom = next(s for s in CERTIFICATION_STEPS if s.name == "05-sbom-provenance")
        assert sbom.unimplemented, (
            "no real SBOM/provenance generation exists; the step must be recorded "
            "unimplemented, not substituted with a nearby static check"
        )
        assert "build-reproducibility-check" not in " ".join(sbom.command)
