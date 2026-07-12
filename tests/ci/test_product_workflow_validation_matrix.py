from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs" / "validation" / "master_workflow_traceability_matrix.md"
MAKEFILE = ROOT / "Makefile"
PR_CHECKS_WORKFLOW = ROOT / ".github" / "workflows" / "pr-checks.yml"


def _matrix_text() -> str:
    return MATRIX.read_text(encoding="utf-8")


def test_product_workflow_validation_matrix_exists() -> None:
    assert MATRIX.exists()


def test_matrix_defines_required_status_vocabulary() -> None:
    text = _matrix_text()

    for status in (
        "`covered`",
        "`partially_covered`",
        "`missing`",
        "`requires_live_environment`",
        "`requires_provider_or_external_integration`",
    ):
        assert status in text


def test_matrix_references_key_validation_suites_and_sources() -> None:
    text = _matrix_text()

    for suite in (
        "Golden Path E2E",
        "Layer-by-Layer Validation",
        "Security/Tenant Isolation",
        "Agent Grounding and Governance",
        "Calculation and Evidence Integrity",
        "Operational Resilience",
    ):
        assert suite in text

    for coverage_source in (
        "apps/web/e2e/journeys/",
        "tests/backend_integrated/",
        "tests/security/",
        "tests/integration/",
        "apps/web/e2e/security/",
        "tests/performance/k6/",
    ):
        assert coverage_source in text


def test_matrix_covers_all_canonical_workflow_categories() -> None:
    text = _matrix_text()

    for category in (
        "Authentication, Tenant, and Workspace Access",
        "Account and Prospect Setup",
        "Data Ingestion Workflows",
        "Extraction and Signal Detection",
        "Knowledge Graph and Context Engine",
        "Value Pack Selection and Governance",
        "Prospect Intelligence Workflow",
        "Stakeholder Mapping",
        "Hypothesis Generation Workflow",
        "Value Driver Tree Workflow",
        "Evidence Matching Workflow",
        "Benchmark and Ground Truth Workflow",
        "Formula Selection and Calculation Workflow",
        "Value Calculator Workflow",
        "Business Case Generation Workflow",
        "Narrative and Proposal Workflow",
        "Agentic Chat and Right-Rail Workflow",
        "Review, Approval, and Governance Workflow",
        "Versioning, Audit, and Traceability",
        "Collaboration Workflow",
        "CRM and External System Workflow",
        "Value Realization Workflow",
        "Search and Retrieval Workflow",
        "Notifications and Task Workflow",
        "Admin Configuration Workflow",
        "Security and Compliance User Workflows",
        "Error, Empty State, and Recovery Workflows",
        "Full End-to-End Golden Path",
        "Full End-to-End Adversarial Path",
        "Persona-Based Validation Journeys",
    ):
        assert category in text


def test_matrix_preserves_launch_evidence_boundary() -> None:
    text = _matrix_text()

    assert "This matrix is not launch evidence" in text
    assert "does not close launch gates" in text
    assert "retained artifacts" in text


def test_matrix_guard_is_wired_into_pr_ci() -> None:
    makefile_text = MAKEFILE.read_text(encoding="utf-8")
    pr_checks_text = PR_CHECKS_WORKFLOW.read_text(encoding="utf-8")

    assert "tests/ci/test_product_workflow_validation_matrix.py" in makefile_text
    assert "make check-workflow-matrix" in pr_checks_text
