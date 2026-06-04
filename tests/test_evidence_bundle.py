from __future__ import annotations

import importlib.util
import json
import sys
import tarfile
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts" / "ci" / "generate_evidence_bundle.py"
    spec = importlib.util.spec_from_file_location("generate_evidence_bundle", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stub_generators(module, monkeypatch):
    def launch_scorecard(_repo_root: Path, staging_root: Path, _gaps: list[dict]):
        path = staging_root / "maturity" / "launch-readiness-scorecard.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"summary":{"scores":{"launch_readiness":100}}}\n', encoding="utf-8")
        return {"name": "launch_readiness_scorecard", "output": "maturity/launch-readiness-scorecard.json"}

    def release_packet(_repo_root: Path, staging_root: Path, _release_sha: str, _gaps: list[dict]):
        path = staging_root / "maturity" / "release-evidence-packet" / "release-evidence-summary.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Release Evidence Packet\n", encoding="utf-8")
        return {"name": "release_evidence_packet", "output": "maturity/release-evidence-packet"}

    def command_record(name: str):
        return {"name": name, "returncode": 0}

    monkeypatch.setattr(module, "_generate_launch_scorecard", launch_scorecard)
    monkeypatch.setattr(module, "_generate_release_packet", release_packet)
    monkeypatch.setattr(
        module,
        "_generate_contract_reports",
        lambda _repo_root, _gaps, _staging_root=None: command_record("contracts"),
    )
    monkeypatch.setattr(
        module,
        "_generate_migration_status",
        lambda _repo_root, _gaps, _staging_root=None: command_record("migrations"),
    )


def _write_minimal_repo(repo_root: Path) -> None:
    (repo_root / ".github" / "workflows").mkdir(parents=True)
    (repo_root / ".github" / "workflows" / "release.yml").write_text(
        "name: Release\non: workflow_dispatch\njobs:\n  bundle:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )
    (repo_root / "monitoring" / "grafana" / "dashboards").mkdir(parents=True)
    (repo_root / "monitoring" / "grafana" / "dashboards" / "overview.json").write_text(
        '{"title":"Overview","panels":[]}\n',
        encoding="utf-8",
    )
    (repo_root / "monitoring" / "prometheus").mkdir(parents=True)
    (repo_root / "monitoring" / "prometheus" / "rules.yml").write_text("groups: []\n", encoding="utf-8")
    (repo_root / "k8s" / "envs").mkdir(parents=True)
    (repo_root / "k8s" / "envs" / "staging.yaml").write_text("apiVersion: v1\nkind: Namespace\n", encoding="utf-8")


def test_generate_evidence_bundle_creates_archive_and_manifest(tmp_path, monkeypatch):
    module = _load_module()
    _stub_generators(module, monkeypatch)
    _write_minimal_repo(tmp_path)
    artifacts = tmp_path / "artifacts"
    (artifacts / "frontend").mkdir(parents=True)
    (artifacts / "frontend" / "junit.xml").write_text("<testsuite />\n", encoding="utf-8")
    (artifacts / "scan").mkdir(parents=True)
    (artifacts / "scan" / "sbom-layer1-test.cdx.json").write_text('{"bomFormat":"CycloneDX"}\n', encoding="utf-8")
    (artifacts / "release_smoke").mkdir(parents=True)
    (artifacts / "release_smoke" / "release_smoke_junit.xml").write_text("<testsuite />\n", encoding="utf-8")

    summary = module.generate_evidence_bundle(
        repo_root=tmp_path,
        output_dir=tmp_path / "artifacts" / "evidence",
        release_sha="abcdef1234567890",
    )

    archive = tmp_path / summary["archive_path"]
    assert archive.exists()
    assert (tmp_path / "artifacts" / "evidence" / "LATEST").read_text(encoding="utf-8").strip() == archive.name

    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        assert names == sorted(names)
        assert "manifest.json" in names
        assert "README.md" in names
        assert "maturity/launch-readiness-scorecard.json" in names
        assert "tests/artifacts/frontend/junit.xml" in names
        assert "supply-chain/artifacts/scan/sbom-layer1-test.cdx.json" in names
        manifest = json.loads(tar.extractfile("manifest.json").read().decode("utf-8"))  # type: ignore[union-attr]

        by_name = {entry["archive_path"]: entry for entry in manifest["files"]}
        for name in names:
            if name == "manifest.json":
                continue
            data = tar.extractfile(name).read()  # type: ignore[union-attr]
            assert by_name[name]["size_bytes"] == len(data)
            assert by_name[name]["sha256"] == module.hashlib.sha256(data).hexdigest()


def test_missing_optional_heavy_artifacts_become_gaps(tmp_path, monkeypatch):
    module = _load_module()
    _stub_generators(module, monkeypatch)
    _write_minimal_repo(tmp_path)

    summary = module.generate_evidence_bundle(
        repo_root=tmp_path,
        output_dir=tmp_path / "artifacts" / "evidence",
        release_sha="abcdef1234567890",
    )

    archive = tmp_path / summary["archive_path"]
    with tarfile.open(archive, "r:gz") as tar:
        manifest = json.loads(tar.extractfile("manifest.json").read().decode("utf-8"))  # type: ignore[union-attr]

    assert summary["evidence_gap_count"] > 0
    assert any(gap["reason"] == "optional_heavy_evidence_missing" for gap in manifest["evidence_gaps"])


def test_root_package_json_exposes_evidence_bundle_script():
    root = Path(__file__).resolve().parents[1]
    package_json = json.loads((root / "package.json").read_text(encoding="utf-8"))
    assert package_json["scripts"]["evidence:bundle"] == "python scripts/ci/generate_evidence_bundle.py"
