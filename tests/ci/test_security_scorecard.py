"""Test Security Scorecard generation."""

from __future__ import annotations

import pytest
from scripts.ci.security_scorecard import evaluate_security_posture


def test_security_scorecard_achieves_target():
    report = evaluate_security_posture()
    assert report["achieved_score"] >= 8.8
    assert report["target_met"] is True
    assert "Area_A_Security_Aggregate_Required" in report["area_scores"]
    assert "Area_B_Hostile_Tenancy_Coverage" in report["area_scores"]
    assert "Area_C_Supply_Chain_Hardening" in report["area_scores"]
    assert "Area_D_Secrets_Management_Canonicalization" in report["area_scores"]
    assert "Area_E_Production_Security_Validation" in report["area_scores"]
