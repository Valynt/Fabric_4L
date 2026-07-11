from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PEN_TEST_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "penetration-testing.yml"
NIKTO_SCRIPT = REPO_ROOT / "tests" / "penetration" / "nikto-scan.sh"


def test_penetration_testing_workflow_references_existing_nikto_script() -> None:
    workflow_text = PEN_TEST_WORKFLOW.read_text(encoding="utf-8")
    assert "tests/penetration/nikto-scan.sh" in workflow_text
    assert NIKTO_SCRIPT.exists()
