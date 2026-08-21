from __future__ import annotations

import datetime
from pathlib import Path

import yaml

from scripts.ci.check_trivy_ignore_policy import validate_trivy_ignore

ROOT = Path(__file__).resolve().parents[2]


def test_real_trivyignore_file_is_valid() -> None:
    path = ROOT / ".trivyignore.yaml"
    assert path.exists(), ".trivyignore.yaml should exist at repository root"
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    violations = validate_trivy_ignore(
        content, reference_date=datetime.date(2025, 1, 1)
    )
    assert violations == [], f"Unexpected violations in .trivyignore.yaml: {violations}"


def test_detects_expired_waivers() -> None:
    sample = {
        "misconfigurations": [
            {
                "id": "AWS-0040",
                "paths": ["terraform-aws-modules/eks/aws/main.tf"],
                "statement": "Upstream EKS module defaults public cluster endpoint; restricted by security groups.",
                "expired_at": "2024-01-01",
            }
        ]
    }
    violations = validate_trivy_ignore(sample, reference_date=datetime.date(2025, 1, 1))
    assert any(v.field == "expired_at" and "expired" in v.message for v in violations)


def test_detects_missing_required_fields() -> None:
    sample = {
        "misconfigurations": [
            {
                "id": "AWS-0040",
                "paths": ["terraform-aws-modules/eks/aws/main.tf"],
                # missing statement and expired_at
            }
        ]
    }
    violations = validate_trivy_ignore(sample, reference_date=datetime.date(2025, 1, 1))
    fields = [v.field for v in violations]
    assert "statement" in fields
    assert "expired_at" in fields


def test_detects_duplicate_ids() -> None:
    sample = {
        "misconfigurations": [
            {
                "id": "KSV-0014",
                "paths": ["k8s/**"],
                "statement": "Legacy stateful and observability images require writable runtime paths.",
                "expired_at": "2026-11-18",
            },
            {
                "id": "KSV-0014",
                "paths": ["infra/helm/**"],
                "statement": "Duplicate rule statement here.",
                "expired_at": "2026-11-18",
            },
        ]
    }
    violations = validate_trivy_ignore(sample, reference_date=datetime.date(2025, 1, 1))
    assert any("Duplicate ID" in v.message for v in violations)


def test_detects_overly_broad_globs() -> None:
    sample = {
        "vulnerabilities": [
            {
                "id": "CVE-2026-12345",
                "paths": ["*"],
                "statement": "Overly broad rule statement for testing purposes.",
                "expired_at": "2026-11-18",
            }
        ]
    }
    violations = validate_trivy_ignore(sample, reference_date=datetime.date(2025, 1, 1))
    assert any("Overly broad path pattern" in v.message for v in violations)


def test_detects_repo_wide_glob_equivalents() -> None:
    sample = {
        "vulnerabilities": [
            {
                "id": "CVE-2026-12345",
                "paths": ["**/*", "**/**/*", "./**/*", "**/*/**", "***"],
                "statement": "Repository-wide suppression must be rejected by the policy.",
                "expired_at": "2026-11-18",
            }
        ]
    }
    violations = validate_trivy_ignore(sample, reference_date=datetime.date(2025, 1, 1))
    broad = [v for v in violations if "whole repository tree" in v.message]
    assert broad, f"Expected whole-repository glob violations, got: {violations}"


def test_allows_narrow_glob_paths() -> None:
    sample = {
        "misconfigurations": [
            {
                "id": "KSV-0014",
                "paths": ["k8s/**", "infra/helm/fabric-chart/charts/**"],
                "statement": "Narrow glob under a real checkout path is allowed.",
                "expired_at": "2026-11-18",
            }
        ]
    }
    violations = validate_trivy_ignore(sample, reference_date=datetime.date(2025, 1, 1))
    assert violations == [], f"Expected no violations for narrow globs: {violations}"


def test_detects_short_rationale_statement() -> None:
    sample = {
        "misconfigurations": [
            {
                "id": "KSV-0014",
                "paths": ["k8s/**"],
                "statement": "Too short",
                "expired_at": "2026-11-18",
            }
        ]
    }
    violations = validate_trivy_ignore(sample, reference_date=datetime.date(2025, 1, 1))
    assert any(v.field == "statement" for v in violations)
