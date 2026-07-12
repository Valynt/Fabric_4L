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


def test_cli_defaults_use_canonical_baseline_paths() -> None:
    module = _load_module()
    parser = module.build_parser()

    args = parser.parse_args([])

    assert args.policy == "config/baselines/layer-quality-threshold-policy.json"
    assert args.output == "config/baselines/layer-quality-scorecard.json"
    assert args.summary == "artifacts/layer-quality-scorecard.md"
    assert args.attention_registry == "config/baselines/layer-quality-attention-registry.json"


def _write_attention_registry(tmp_path: Path, payload: dict) -> str:
    registry = tmp_path / "config" / "baselines" / "layer-quality-attention-registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps(payload), encoding="utf-8")
    return "config/baselines/layer-quality-attention-registry.json"


def _touch(tmp_path: Path, rel_path: str) -> None:
    target = tmp_path / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("governed evidence", encoding="utf-8")


def test_attention_registry_parses_and_passes_governed_items(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    for rel_path in (
        "generated/layer4_agents.ts",
        "contracts/openapi/layer4-agents.json",
        "docs/governance/layer-quality-attention-records.md",
        "monitoring/alerting/rules-production.yml",
        "docs/operations/runbooks/database-pool-exhaustion.md",
        ".agent/harness/conductor.py",
    ):
        _touch(tmp_path, rel_path)
    registry_path = _write_attention_registry(
        tmp_path,
        {
            "ungoverned_hotspots": [
                {
                    "id": "hotspot",
                    "path": "generated/layer4_agents.ts",
                    "owner": "@platform-contracts",
                    "evidence_path": "docs/governance/layer-quality-attention-records.md",
                    "governing_decision": "generated contract source of truth",
                    "generated": True,
                    "source_contract": "contracts/openapi/layer4-agents.json",
                    "generation_command": "corepack pnpm run check:api-types",
                    "review_due": "2026-09-30",
                    "remediation_state": "governed",
                }
            ],
            "stale_decisions": [
                {
                    "id": "alert",
                    "path": "monitoring/alerting/rules-production.yml",
                    "owner": "@platform-sre",
                    "evidence_path": "docs/governance/layer-quality-attention-records.md",
                    "runbook_path": "docs/operations/runbooks/database-pool-exhaustion.md",
                    "decision_date": "2026-06-21",
                    "decision": "keep threshold",
                    "review_due": "2026-09-30",
                    "remediation_state": "fresh",
                }
            ],
            "knowledge_silos": [
                {
                    "id": "silo",
                    "path": ".agent/harness/conductor.py",
                    "owner": "Brian",
                    "secondary_owner": "@platform-agent-runtime",
                    "evidence_path": "docs/governance/layer-quality-attention-records.md",
                    "review_due": "2026-09-30",
                    "remediation_state": "backup-owner-assigned",
                }
            ],
        },
    )

    attention = module.compute_attention(registry_path, today=module.date(2026, 6, 21))

    assert attention["status"] == "pass"
    assert attention["failed_items"] == 0


def test_missing_governing_decision_fails_attention_hotspot(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    _touch(tmp_path, "api/models.py")
    _touch(tmp_path, "docs/governance/layer-quality-attention-records.md")
    registry_path = _write_attention_registry(
        tmp_path,
        {
            "ungoverned_hotspots": [
                {
                    "id": "hotspot",
                    "path": "api/models.py",
                    "owner": "@layer3-knowledge",
                    "evidence_path": "docs/governance/layer-quality-attention-records.md",
                    "review_due": "2026-09-30",
                    "remediation_state": "governed",
                }
            ],
            "stale_decisions": [],
            "knowledge_silos": [],
        },
    )

    attention = module.compute_attention(registry_path, today=module.date(2026, 6, 21))

    item = attention["sections"]["ungoverned_hotspots"][0]
    assert attention["status"] == "fail"
    assert item["status"] == "fail"
    assert "missing governing_decision" in item["failures"]


def test_stale_decision_review_due_fails_attention(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    _touch(tmp_path, "monitoring/alerting/rules-production.yml")
    _touch(tmp_path, "docs/governance/layer-quality-attention-records.md")
    _touch(tmp_path, "docs/operations/runbooks/database-pool-exhaustion.md")
    registry_path = _write_attention_registry(
        tmp_path,
        {
            "ungoverned_hotspots": [],
            "stale_decisions": [
                {
                    "id": "alert",
                    "path": "monitoring/alerting/rules-production.yml",
                    "owner": "@platform-sre",
                    "evidence_path": "docs/governance/layer-quality-attention-records.md",
                    "runbook_path": "docs/operations/runbooks/database-pool-exhaustion.md",
                    "decision_date": "2026-01-01",
                    "decision": "keep threshold",
                    "review_due": "2026-06-20",
                    "remediation_state": "fresh",
                }
            ],
            "knowledge_silos": [],
        },
    )

    attention = module.compute_attention(registry_path, today=module.date(2026, 6, 21))

    failures = attention["sections"]["stale_decisions"][0]["failures"]
    assert attention["status"] == "fail"
    assert "review_due is stale: 2026-06-20" in failures


def test_generated_hotspot_requires_source_contract_and_generation_command(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    _touch(tmp_path, "generated/l4/index.ts")
    _touch(tmp_path, "docs/governance/layer-quality-attention-records.md")
    registry_path = _write_attention_registry(
        tmp_path,
        {
            "ungoverned_hotspots": [
                {
                    "id": "generated",
                    "path": "generated/l4/index.ts",
                    "owner": "@frontend-platform",
                    "evidence_path": "docs/governance/layer-quality-attention-records.md",
                    "governing_decision": "generated API type",
                    "generated": True,
                    "review_due": "2026-09-30",
                    "remediation_state": "governed",
                }
            ],
            "stale_decisions": [],
            "knowledge_silos": [],
        },
    )

    attention = module.compute_attention(registry_path, today=module.date(2026, 6, 21))

    failures = attention["sections"]["ungoverned_hotspots"][0]["failures"]
    assert attention["status"] == "fail"
    assert "missing source_contract: None" in failures
    assert "missing generation_command" in failures


def test_knowledge_silo_normalizes_missing_init_path_and_requires_backup_owner(tmp_path: Path, monkeypatch) -> None:
    module = _load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    _touch(tmp_path, ".agent/harness/hooks/__init__.py")
    _touch(tmp_path, "docs/governance/layer-quality-attention-records.md")
    registry_path = _write_attention_registry(
        tmp_path,
        {
            "ungoverned_hotspots": [],
            "stale_decisions": [],
            "knowledge_silos": [
                {
                    "id": "silo",
                    "path": ".agent/harness/hooks/init.py",
                    "owner": "Brian",
                    "evidence_path": "docs/governance/layer-quality-attention-records.md",
                    "review_due": "2026-09-30",
                    "remediation_state": "normalized",
                }
            ],
        },
    )

    attention = module.compute_attention(registry_path, today=module.date(2026, 6, 21))

    item = attention["sections"]["knowledge_silos"][0]
    assert item["path"] == ".agent/harness/hooks/__init__.py"
    assert item["reported_path"] == ".agent/harness/hooks/init.py"
    assert "missing secondary_owner or backup_owner" in item["failures"]
