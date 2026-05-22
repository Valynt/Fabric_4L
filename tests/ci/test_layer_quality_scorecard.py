from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "layer_quality_scorecard.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("layer_quality_scorecard", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_compute_scopes_support_files_to_matching_layer(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)

    (tmp_path / "services" / "layer2-extraction" / "tests").mkdir(parents=True)
    (tmp_path / "services" / "layer2-extraction" / "tests" / "test_tenant_isolation.py").write_text(
        "tenant isolation unauthorized forbidden auth schema migration",
        encoding="utf-8",
    )
    (tmp_path / "contracts" / "openapi").mkdir(parents=True)
    (tmp_path / "contracts" / "openapi" / "layer2-extraction.json").write_text(
        json.dumps({"openapi": "3.1.0", "info": {"title": "Layer 2"}}),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "shared-quality-notes.md").write_text(
        "tenant isolation unauthorized forbidden auth schema migration docs",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "layer2-extraction-contracts.md").write_text(
        "Layer 2 docs contract freshness schema docs",
        encoding="utf-8",
    )

    policy = {"version": "1.0.0", "thresholds": {"per_layer_min_score": 80, "max_failed_layers": 6}}

    report = module.compute(policy)

    assert report["layers"]["layer2"]["score"] == 100.0
    assert report["layers"]["layer2"]["passed_checks"] == 5
    assert all(check["present"] is True for check in report["layers"]["layer2"]["checks"].values())
    assert report["layers"]["layer1"]["score"] == 0.0
    assert report["layers"]["layer1"]["checks"]["contract_tests"]["present"] is False
    assert report["layers"]["layer1"]["checks"]["security_negative_paths"]["present"] is False
    assert report["layers"]["layer1"]["checks"]["docs_contract_freshness"]["present"] is False
