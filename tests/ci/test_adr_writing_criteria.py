from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ADR_README = REPO_ROOT / "docs" / "explanations" / "adr" / "README.md"


def test_adr_readme_defines_when_to_write_an_adr() -> None:
    readme = ADR_README.read_text(encoding="utf-8")

    assert "## When to Write an ADR" in readme
    assert "Layer boundaries or canonical runtime paths" in readme
    assert "Cross-service contracts" in readme
    assert "Tenant isolation, security, or compliance posture" in readme
    assert "Production infrastructure or managed-service strategy" in readme
    assert "## When Not to Write an ADR" in readme


def test_adr_readme_requires_decision_evidence() -> None:
    readme = ADR_README.read_text(encoding="utf-8")

    assert "## ADR Review Criteria" in readme
    assert "problem statement" in readme
    assert "alternatives considered" in readme
    assert "validation or enforcement path" in readme
    assert "owner and follow-up obligations" in readme
