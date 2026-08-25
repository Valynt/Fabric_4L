"""Regression contracts for security gates that must work in this organization."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "security-gates.yml"
AUDIT_GRAPH = (
    ROOT
    / "services"
    / "layer4-agents"
    / "src"
    / "layer4_agents"
    / "agents"
    / "audit_orchestrator"
    / "graph.py"
)
AUDIT_PERSISTENCE = AUDIT_GRAPH.with_name("persistence.py")


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_gitleaks_uses_pinned_oss_cli_without_org_license_action() -> None:
    workflow = _workflow()
    job = workflow["jobs"]["gitleaks-scan"]
    rendered = WORKFLOW.read_text(encoding="utf-8")
    run_scripts = "\n".join(step.get("run", "") for step in job["steps"])

    assert "gitleaks/gitleaks-action" not in rendered
    assert "github.com/zricethezav/gitleaks/v8@${GITLEAKS_VERSION}" in run_scripts
    assert "GITLEAKS_VERSION" in job["steps"][-1]["env"]
    assert job["steps"][-1]["env"]["GITLEAKS_VERSION"].startswith("v8.")
    assert "--config .gitleaks.toml" in run_scripts


def test_zap_scans_existing_public_health_endpoints() -> None:
    workflow = _workflow()
    job = workflow["jobs"]["dast-api-scan"]
    scan = next(step for step in job["steps"] if step.get("name", "").startswith("Run OWASP"))

    for port in range(8001, 8007):
        assert f"http://127.0.0.1:{port}/health" in scan["run"]


def test_audit_graph_writes_are_tenant_scoped() -> None:
    graph = AUDIT_GRAPH.read_text(encoding="utf-8")
    persistence = AUDIT_PERSISTENCE.read_text(encoding="utf-8")
    writer = persistence[persistence.index("async def _write_kg_tx(") :]

    assert "if not config.tenant_id:" in graph
    assert "tenant_id=config.tenant_id" in graph
    assert "tenant_id: str" in writer.split(") -> None:", 1)[0]

    node_merges = [
        line for line in writer.splitlines() if "MERGE (" in line and "-[" not in line
    ]
    assert node_merges
    assert all("tenant_id:" in line for line in node_merges)
