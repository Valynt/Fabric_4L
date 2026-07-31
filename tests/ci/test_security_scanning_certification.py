import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _workflow(name: str) -> tuple[str, dict]:
    text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def test_codeql_actions_are_immutable_and_queries_are_explicit() -> None:
    text, _ = _workflow("codeql.yml")
    assert "actions/checkout@v" not in text
    assert "github/codeql-action/init@v" not in text
    assert "github/codeql-action/analyze@v" not in text
    assert "queries: security-extended,security-and-quality" in text


def test_structural_preflight_uses_immutable_pnpm_setup_action() -> None:
    text, _ = _workflow("pr-checks.yml")
    assert "pnpm/action-setup@v" not in text
    assert "pnpm/action-setup@fc06bc1257f339d1d5d8b3a19a8cae5388b55320" in text


def test_dast_cannot_manufacture_or_soft_pass_results() -> None:
    text, workflow = _workflow("penetration-testing.yml")
    assert "generating fallback results" not in text
    assert "--timeout 1200 || true" not in text
    assert "Don't fail CI" not in text
    assert "zap_completed\": true" not in text
    assert "nikto_completed\": true" not in text
    assert "steps.zap_scan.outputs.policy_status" in text
    assert text.count("Active DAST is restricted to the workflow-owned loopback test stack") == 2
    upload = next(
        step
        for step in workflow["jobs"]["zap-scan"]["steps"]
        if step.get("name") == "Upload SARIF to GitHub Security"
    )
    assert "convert_sarif.outcome == 'success'" in upload["if"]


def test_release_sbom_delegates_to_canonical_supply_chain_workflow() -> None:
    text, workflow = _workflow("sbom.yml")
    assert "uses: ./.github/workflows/supply-chain-integrity.yml" in text
    assert "certify_images: true" in text
    assert "actions/checkout@v" not in text
    assert "pnpm/action-setup@v" not in text
    assert set(workflow["jobs"]) == {"certify-release-artifacts"}


def test_supply_chain_summary_fails_closed() -> None:
    text, _ = _workflow("supply-chain-integrity.yml")
    assert "Validate prerequisite results" in text
    assert "inputs.certify_images || github.event_name == 'workflow_dispatch'" in text
    assert '[ "${{ inputs.certify_images }}" = "true" ]' in text
    assert "Enforce dependency findings policy" in text
    assert 'exit 1' in text[text.index("Validate prerequisite results") :]
    assert "SLSA provenance attestations created" not in text


def test_machine_readable_inventory_and_findings_validate() -> None:
    inventory = json.loads(
        (ROOT / "security" / "scanning" / "tool-inventory.json").read_text(encoding="utf-8")
    )
    findings = json.loads(
        (ROOT / "security" / "scanning" / "consolidated-findings.json").read_text(
            encoding="utf-8"
        )
    )
    assert inventory["schema_version"] == "1.0.0"
    assert len(inventory["tools"]) >= 15
    assert all(tool["owner"] and tool["scope"] and tool["version"] for tool in inventory["tools"])
    assert findings["schema_version"] == "1.0.0"
    assert all(item["disposition"] for item in findings["findings"])
