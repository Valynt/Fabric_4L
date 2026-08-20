from pathlib import Path


def test_temporal_command_is_policy_free_delegate() -> None:
    source = Path("scripts/ci/check_temporal_skips.py").read_text(encoding="utf-8")
    assert "test_debt_governance_delegate import delegate" in source
    assert "TEMPORAL_KEYWORDS" not in source
    assert "test_skip_register.yaml" not in source
