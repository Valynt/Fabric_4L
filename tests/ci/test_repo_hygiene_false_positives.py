"""False-positive coverage for repository hygiene path scanning."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "ci"))
from repo_hygiene import scan_production_frontend_client_references, scan_workflows


def _manifest():
    return {
        "obsolete": [
            {"path": "frontend", "severity": "error"},
            {"path": "value-fabric", "severity": "error"},
        ]
    }


def test_workflow_service_metadata_is_not_obsolete_path(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "critical-gates.yml").write_text(
        "jobs:\n  gate:\n    strategy:\n      matrix:\n        include:\n"
        "          - id: generated-client-reproducibility\n"
        "            service: frontend\n"
        "            owner: '@value-fabric/frontend-leads'\n",
        encoding="utf-8",
    )

    assert scan_workflows(tmp_path, _manifest()) == []


def test_workflow_cluster_name_is_not_obsolete_path(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "deploy.yml").write_text(
        "env:\n  EKS_CLUSTER_NAME: 'value-fabric'\n",
        encoding="utf-8",
    )

    assert scan_workflows(tmp_path, _manifest()) == []


def test_audit_note_with_legacy_frontend_path_is_allowed(tmp_path):
    docs = tmp_path / "docs" / "operations"
    docs.mkdir(parents=True)
    (docs / "COMMAND_REFERENCE.md").write_text(
        "> **Audit note:** This reference uses legacy commands and directory paths "
        "(`frontend/`) that do not match current monorepo conventions. "
        "Use `apps/web/` for canonical paths.\n",
        encoding="utf-8",
    )

    assert scan_production_frontend_client_references(tmp_path) == []
