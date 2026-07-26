from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts/ci/validate_helm_dependencies.py"
WORKFLOW = REPO_ROOT / ".github/workflows/security-gates.yml"
HELM_VERSION = "v3.16.2"
DEPENDENCIES = {
    "postgresql": "13.2.0",
    "redis": "18.5.0",
    "ingress-nginx": "4.8.3",
}


def _write_lock(chart_dir: Path) -> None:
    dependencies = "\n".join(
        f"- name: {name}\n  repository: https://charts.example.test/{name}\n  version: {version}"
        for name, version in DEPENDENCIES.items()
    )
    (chart_dir / "Chart.lock").write_text(
        f"dependencies:\n{dependencies}\ndigest: sha256:lock-digest\ngenerated: test\n",
        encoding="utf-8",
    )


def _write_archive(
    chart_dir: Path,
    name: str,
    version: str,
    *,
    filename: str | None = None,
    subcharts: dict[str, str] | None = None,
) -> Path:
    charts_dir = chart_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    archive = charts_dir / (filename or f"{name}-{version}.tgz")
    chart_yaml = f"apiVersion: v2\nname: {name}\nversion: {version}\n".encode()
    with tarfile.open(archive, "w:gz") as bundle:
        info = tarfile.TarInfo(f"{name}/Chart.yaml")
        info.size = len(chart_yaml)
        bundle.addfile(info, io.BytesIO(chart_yaml))
        for subchart_name, subchart_version in (subcharts or {}).items():
            subchart_yaml = (
                f"apiVersion: v2\nname: {subchart_name}\nversion: {subchart_version}\n"
            ).encode()
            subchart_info = tarfile.TarInfo(
                f"{name}/charts/{subchart_name}/Chart.yaml"
            )
            subchart_info.size = len(subchart_yaml)
            bundle.addfile(subchart_info, io.BytesIO(subchart_yaml))
    return archive


@pytest.fixture
def prepared_chart(tmp_path: Path) -> tuple[Path, Path]:
    chart_dir = tmp_path / "fabric-chart"
    chart_dir.mkdir()
    _write_lock(chart_dir)
    for name, version in DEPENDENCIES.items():
        _write_archive(chart_dir, name, version)
    evidence_dir = tmp_path / "artifacts/helm-dependencies"
    return chart_dir, evidence_dir


def _run_validator(
    mode: str, chart_dir: Path, evidence_dir: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            mode,
            "--chart-dir",
            str(chart_dir),
            "--evidence-dir",
            str(evidence_dir),
            "--helm-version",
            HELM_VERSION,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def _generate(prepared_chart: tuple[Path, Path]) -> tuple[Path, Path]:
    chart_dir, evidence_dir = prepared_chart
    result = _run_validator("generate", chart_dir, evidence_dir)
    assert result.returncode == 0, result.stderr
    return chart_dir, evidence_dir


def test_generate_accepts_archives_with_nested_subchart_metadata(
    prepared_chart: tuple[Path, Path],
) -> None:
    chart_dir, evidence_dir = prepared_chart
    archive = chart_dir / "charts/postgresql-13.2.0.tgz"
    archive.unlink()
    _write_archive(
        chart_dir,
        "postgresql",
        "13.2.0",
        subcharts={"common": "2.14.1"},
    )

    result = _run_validator("generate", chart_dir, evidence_dir)

    assert result.returncode == 0, result.stderr


def test_generate_and_validate_records_lock_and_archive_integrity(
    prepared_chart: tuple[Path, Path],
) -> None:
    chart_dir, evidence_dir = _generate(prepared_chart)

    metadata = json.loads((evidence_dir / "metadata.json").read_text())
    assert metadata["chart_lock_sha256"] == hashlib.sha256(
        (chart_dir / "Chart.lock").read_bytes()
    ).hexdigest()
    assert metadata["helm_version"] == HELM_VERSION
    assert {(item["name"], item["version"]) for item in metadata["dependencies"]} == set(
        DEPENDENCIES.items()
    )
    assert len((evidence_dir / "checksums.sha256").read_text().splitlines()) == 3
    assert _run_validator("validate", chart_dir, evidence_dir).returncode == 0


@pytest.mark.parametrize("mutation", ["missing", "extra", "renamed", "wrong-version"])
def test_generate_rejects_archive_set_or_identity_drift(
    prepared_chart: tuple[Path, Path], mutation: str
) -> None:
    chart_dir, evidence_dir = prepared_chart
    if mutation == "missing":
        (chart_dir / "charts/redis-18.5.0.tgz").unlink()
    elif mutation == "extra":
        _write_archive(chart_dir, "unexpected", "1.0.0")
    elif mutation == "renamed":
        archive = chart_dir / "charts/redis-18.5.0.tgz"
        archive.rename(chart_dir / "charts/renamed-18.5.0.tgz")
    else:
        archive = chart_dir / "charts/redis-18.5.0.tgz"
        archive.unlink()
        _write_archive(chart_dir, "redis", "18.5.1", filename="redis-18.5.0.tgz")

    result = _run_validator("generate", chart_dir, evidence_dir)

    assert result.returncode != 0
    assert "Helm dependency validation failed" in result.stderr


def test_validate_rejects_checksum_mismatch(
    prepared_chart: tuple[Path, Path],
) -> None:
    chart_dir, evidence_dir = _generate(prepared_chart)
    with (chart_dir / "charts/redis-18.5.0.tgz").open("ab") as archive:
        archive.write(b"tampered")

    result = _run_validator("validate", chart_dir, evidence_dir)

    assert result.returncode != 0
    assert "checksum" in result.stderr.lower()


def test_security_workflow_separates_preparation_from_trivy() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    preparation = workflow.split("  prepare-helm-dependencies:", 1)[1].split(
        "  trivy-repo-scan:", 1
    )[0]
    trivy = workflow.split("  trivy-repo-scan:", 1)[1].split(
        "\n  # OSV-Scanner", 1
    )[0]

    assert "actions/cache@5a3ec84eff668545956fd18022155c47e93e2684" in preparation
    assert (
        "helm-deps-${{ runner.os }}-${{ runner.arch }}-helm-v3.16.2-"
        "${{ hashFiles('infra/helm/fabric-chart/Chart.lock') }}"
    ) in preparation
    assert "restore-keys:" not in preparation
    assert "if: steps.helm-cache.outputs.cache-hit == 'true'" in preparation
    assert (
        "if: steps.helm-cache.outputs.cache-hit != 'true' || "
        "steps.cache-validation.outcome != 'success'"
    ) in preparation
    assert "rm -rf infra/helm/fabric-chart/charts artifacts/helm-dependencies" in preparation
    assert "timeout 60s helm repo" in preparation
    assert "timeout 180s helm dependency build" in preparation
    assert "for attempt in 1 2 3" in preparation
    assert "validate_helm_dependencies.py generate" in preparation
    assert "validate_helm_dependencies.py validate" in preparation
    assert "if: always()" in preparation
    assert "helm-preparation-diagnostics-${{github.sha}}" in preparation
    assert "helm-prepared-dependencies-${{github.sha}}" in preparation
    assert preparation.index("Validate prepared Helm dependencies") < preparation.index(
        "Upload validated Helm dependencies"
    )
    assert "git diff --exit-code" in preparation
    assert "Run Trivy repository scanner" not in preparation
    assert "needs: prepare-helm-dependencies" in trivy
    assert "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093" in trivy
    assert "validate_helm_dependencies.py validate" in trivy
    assert "helm dependency list" in trivy
    assert "helm repo add" not in trivy
    assert "helm dependency build" not in trivy
    assert "git diff --exit-code" in trivy
    assert "Run Trivy repository scanner" in trivy
    assert "trivy-config: 'config/trivy/repository.yaml'" in trivy
    assert trivy.index("validate_helm_dependencies.py validate") < trivy.index(
        "Run Trivy repository scanner"
    )
    assert "helm dependency update" not in workflow


def test_trivy_repository_config_supplies_helm_render_secrets() -> None:
    config_path = REPO_ROOT / "config/trivy/repository.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    helm_sets = config["misconfiguration"]["helm"]["set"]
    assert "global.serviceAuthSecret=ci-render-service-auth-placeholder" in helm_sets
    assert "global.jwtSecret=ci-render-jwt-placeholder" in helm_sets


def test_repository_does_not_track_helm_archives() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "*.tgz"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert tracked.stdout.strip() == ""


def test_release_evidence_bundle_uses_valid_download_artifact_pin() -> None:
    workflow = (REPO_ROOT / ".github/workflows/release-evidence-bundle.yml").read_text(
        encoding="utf-8"
    )

    assert "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093" in workflow
    assert "actions/download-artifact@fa0a91b85d4f404e444306234a53f49b9be1f8b9" not in workflow
