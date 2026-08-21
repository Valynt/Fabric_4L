"""Step registry and runner for the v1 release-factory harness.

Every step delegates to an EXISTING make target, pnpm script, pytest suite, or
scripts/ci checker. This module defines no new gates (INV-FACTORY-001); it
only sequences and records them.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from models import NOT_RUN_EXIT_CODE, Step, StepResult, utc_now

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Phase 1 baseline gates (clean checkout; validates, never repairs).
BASELINE_STEPS: tuple[Step, ...] = (
    Step("setup", ("make", "setup"), "environment"),
    Step("verify", ("make", "verify"), "local verification"),
    Step(
        "production-readiness-gate",
        ("make", "production-readiness-gate"),
        "production readiness",
    ),
    Step("behavior-contract", ("make", "check-behavior-contract"), "behavior contract"),
    Step(
        "behavior-readiness-audit",
        ("make", "check-behavior-readiness-audit"),
        "behavior readiness",
    ),
)

# Candidate certification sequence (launch-contract.yaml). Steps marked
# live_only require staging infrastructure and run only with CERTIFY_LIVE=1;
# otherwise they are recorded as not-run and the candidate stays uncertified
# (fail closed).
CERTIFICATION_STEPS: tuple[Step, ...] = (
    Step("02-install-lockfiles", ("pnpm", "install", "--frozen-lockfile"), "environment"),
    Step("02b-python-setup", ("make", "setup"), "environment"),
    Step("03a-verify", ("make", "verify"), "critical journeys"),
    Step(
        "03b-production-readiness-gate",
        ("make", "production-readiness-gate"),
        "critical journeys",
    ),
    Step("03c-tenant-suite", ("pytest", "tests/tenancy", "-q"), "cross-tenant access"),
    Step(
        "03d-behavior-contract",
        ("make", "check-behavior-contract"),
        "behavior contract",
    ),
    Step(
        "03e-behavior-readiness-audit",
        ("make", "check-behavior-readiness-audit"),
        "behavior readiness",
    ),
    Step(
        "03f-database-readiness",
        ("make", "db-production-readiness-gate"),
        "database readiness",
    ),
    Step(
        "03g-release-smoke",
        ("make", "test-backend-integrated-release-smoke"),
        "critical journeys",
        live_only=True,
    ),
    Step(
        "04-production-build",
        ("pnpm", "--dir", "apps/web", "run", "build"),
        "release evidence",
    ),
    Step(
        "04b-docker-build", ("make", "docker-build"), "release evidence", live_only=True
    ),
    Step(
        "05-sbom-provenance",
        ("make", "generate-sbom-and-provenance"),
        "release evidence: deterministic source-bound SBOM",
    ),
    Step(
        "05b-build-reproducibility",
        ("make", "build-reproducibility-check"),
        "release evidence: every deployable image must build byte-identical (deterministic)",
        live_only=True,
    ),
    Step(
        "05c-compose-config-validate",
        ("make", "compose-config-validate"),
        "deployment topology: all release-significant Docker Compose definitions render and harden consistently",
        live_only=True,
    ),
    Step(
        "05d-helm-dependency-validate",
        ("make", "helm-dependency-validate"),
        "deployment topology: locked Helm chart dependencies render from Chart.lock and validate against live archives",
        live_only=True,
    ),
    Step(
        "05e-k8s-production-overlay-validate",
        ("make", "k8s-production-overlay-validate"),
        "deployment topology: Kubernetes production overlays render and validate (kustomize/kubeconform)",
        live_only=True,
    ),
    Step(
        "05f-k8s-manifest-consistency-check",
        ("make", "k8s-manifest-consistency-check"),
        "deployment topology: static cross-service Kubernetes manifest consistency (no cluster)",
    ),
    Step(
        "06-staging-preflight",
        ("make", "preflight"),
        "capacity: staging deploy preflight only — not a staging deploy certification",
        live_only=True,
    ),
    Step(
        "07-migrations-empty-db",
        ("make", "check-migration-postgres-roundtrip"),
        "migration: empty database -> v1",
        live_only=True,
    ),
    Step(
        "08-migrations-expand-contract-check",
        ("make", "db-migrate-check"),
        "migration: existing schema -> v1 (expand-contract static compatibility "
        "check only — not a baseline-schema migration execution)",
        live_only=True,
    ),
    Step(
        "09-critical-browser-journeys",
        ("pnpm", "--dir", "apps/web", "run", "test:e2e"),
        "critical journeys: mocked frontend e2e suite only — live golden-path "
        "certification is V1-GOLDEN-002, not this step",
        live_only=True,
    ),
    Step("10a-security-suite", ("pytest", "tests/security", "-q"), "AI/application security"),
    Step(
        "10b-security-readiness-static",
        ("make", "security-readiness-gate"),
        "AI/application security: static security readiness only — live DAST "
        "evidence is a separate tracked requirement",
        live_only=True,
    ),
    Step("11-load-profiles", ("make", "perf-test"), "capacity", live_only=True),
    Step(
        "12-provider-failure-drills",
        ("pytest", "tests/reliability", "-q"),
        "background jobs",
        live_only=True,
    ),
    Step("13-backup-restore", ("make", "test-backup-drills"), "RPO/RTO", live_only=True),
    Step(
        "14-rollback-policy",
        ("pytest", "tests/release/test_rollback_procedure.py", "-q"),
        "rollback",
    ),
    Step(
        "14b-rollback-script-verification",
        ("python", "scripts/ci/verify_release_rollback.py"),
        "rollback: rollback tooling script verification only — not a staging "
        "rollback rehearsal",
        live_only=True,
    ),
    Step("15-ai-evaluation", ("make", "evals"), "structured AI output", live_only=True),
    Step(
        "16-observability-static-readiness",
        (
            "pytest",
            "tests/release/test_observability_deployment_readiness.py",
            "-q",
            "--no-mandatory-dep-check",
        ),
        "observability: static deployment-readiness policy only — not deployed "
        "dashboard/alert proof",
    ),
    Step(
        "16b-observability-stack-validation",
        ("make", "validate-monitoring-stack"),
        "observability: end-to-end monitoring stack readiness (YAML + compose + "
        "runbook coverage)",
        live_only=True,
    ),
)


def run_step(step: Step, log_dir: Path, *, live: bool) -> StepResult:
    """Execute one step, teeing output to a per-step log. Never remediates."""
    log_path = log_dir / f"{step.name}.log"
    started = utc_now()
    if step.unimplemented:
        log_path.write_text(
            "unimplemented: this release operation does not exist yet; recorded as "
            "not-run so the candidate stays uncertified (fail closed). A nearby "
            "static check may NOT be substituted for the live operation.\n",
            encoding="utf-8",
        )
        return StepResult(
            gate=step.name,
            command=" ".join(step.command),
            exit_code=NOT_RUN_EXIT_CODE,
            started_at=started,
            finished_at=utc_now(),
            log=str(log_path),
            criterion=step.criterion,
            classification="unimplemented",
        )
    if step.live_only and not live:
        log_path.write_text(
            "not-run: requires live staging environment (CERTIFY_LIVE=1)\n",
            encoding="utf-8",
        )
        return StepResult(
            gate=step.name,
            command=" ".join(step.command),
            exit_code=NOT_RUN_EXIT_CODE,
            started_at=started,
            finished_at=utc_now(),
            log=str(log_path),
            criterion=step.criterion,
            classification="not-run",
        )
    t0 = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            step.command, cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    elapsed = time.monotonic() - t0
    # Signal-terminated processes report negative return codes; normalize to the
    # shell convention (128 + signal number) so a signal death can never collide
    # with the not-run sentinel or be mistaken for anything but a failure.
    exit_code = proc.returncode if proc.returncode >= 0 else 128 + abs(proc.returncode)
    print(f"  {step.name}: exit={exit_code} ({elapsed:.1f}s) log={log_path}")
    return StepResult(
        gate=step.name,
        command=" ".join(step.command),
        exit_code=exit_code,
        started_at=started,
        finished_at=utc_now(),
        log=str(log_path),
        criterion=step.criterion,
        classification="pass" if exit_code == 0 else "unclassified",
    )
