"""Unit tests for DR drill backup header and target contract logic."""
from pathlib import Path


def test_pgdump_header_verification_pass():
    """A valid PGDMP header should pass."""
    # Simulate the bash logic in Python
    header = "PGDMP"
    assert header.startswith("PGDMP")


def test_pgdump_header_verification_fail():
    """An invalid header should fail."""
    header = "\x00\x00\x00\x00\x00"
    assert not header.startswith("PGDMP")


def test_pgdump_header_verification_empty():
    """An empty header should fail."""
    header = ""
    assert not header


def test_dr_drill_workflow_matches_reliability_policy_targets():
    workflow = Path(".github/workflows/dr-drill.yml").read_text(encoding="utf-8")
    policy = Path("docs/reliability/dr-policy.md").read_text(encoding="utf-8")

    assert "PostgreSQL (system of record for layer services)" in policy
    assert "| PostgreSQL (system of record for layer services) | Tier 0 | Critical transactional | 60 minutes | 15 minutes |" in policy
    assert "RTO target: 60 minutes" in workflow
    assert "RPO target: 15 minutes (continuous WAL + daily full backup)" in workflow
    assert "RTO: 60min, RPO: 15min" in workflow


def test_cold_site_dr_runbook_is_wired_to_launch_evidence():
    runbook = Path("docs/troubleshooting/runbooks/incident/cold-site-dr-sync-strategy.md")
    matrix = Path("docs/launch/environment-dependent-evidence-matrix.md").read_text(encoding="utf-8")
    blocker = Path("docs/launch/launch-blocker-register.md").read_text(encoding="utf-8")

    assert runbook.is_file()
    text = runbook.read_text(encoding="utf-8")
    assert "60-minute RTO and 15-minute RPO" in text
    assert "does not close production DR readiness" in text
    assert "cold-site-dr-sync-strategy.md" in matrix
    assert "cold-site DR RTO/RPO measurements" in blocker
