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
        """05-sbom-provenance runs the real deterministic source-bound SBOM.

        The step must invoke the genuine SBOM/provenance generator
        (supply_chain_gate.py sbom), not a nearby static check standing in for it.
        """
        sbom = next(s for s in CERTIFICATION_STEPS if s.name == "05-sbom-provenance")
        assert not sbom.unimplemented, (
            "05-sbom-provenance must now be implemented via the real SBOM generator "
            "(make generate-sbom-and-provenance -> supply_chain_gate.py sbom)"
        )
        assert sbom.command == ("make", "generate-sbom-and-provenance")
        assert "build-reproducibility-check" not in " ".join(sbom.command)

    def test_step_names_do_not_overclaim_what_the_command_proves(self) -> None:
        """A step name must describe the evidence its command actually produces.

        Proxy substitutions (a nearby check standing in for the real release
        operation) are named after what they verify; the real operations are
        tracked as V1 tasks instead of being silently claimed.
        """
        by_name = {s.name: s for s in CERTIFICATION_STEPS}
        expected = {
            # make preflight is a pre-deploy checklist, not a staging deploy.
            "06-staging-preflight": ("make", "preflight"),
            # pnpm test:e2e is the mocked frontend suite, not live golden-path
            # certification (that is V1-GOLDEN-002).
            "09-critical-browser-journeys": (
                "pnpm",
                "--dir",
                "apps/web",
                "run",
                "test:e2e",
            ),
            # security-readiness-gate is a static readiness gate, not DAST.
            "10b-security-readiness-static": ("make", "security-readiness-gate"),
            # db-migrate-check is a static expand/contract compatibility check,
            # not a baseline-schema migration execution.
            "08-migrations-expand-contract-check": ("make", "db-migrate-check"),
            # verify_release_rollback.py verifies rollback tooling, it is not a
            # staging rollback rehearsal.
            "14b-rollback-script-verification": (
                "python",
                "scripts/ci/verify_release_rollback.py",
            ),
            # The observability pytest is a static policy check, not deployed
            # dashboard/alert proof.
            "16-observability-static-readiness": (
                "pytest",
                "tests/release/test_observability_deployment_readiness.py",
                "-q",
                "--no-mandatory-dep-check",
            ),
        }
        for name, command in expected.items():
            assert name in by_name, f"missing renamed step {name!r}"
            assert by_name[name].command == command
        for overclaiming in (
            "06-staging-deploy",
            "10b-dast",
            "08-migrations-from-baseline",
            "14b-rollback-rehearsal",
            "16-observability-readiness",
        ):
            assert overclaiming not in by_name, (
                f"step name {overclaiming!r} overclaims what its command proves"
            )
