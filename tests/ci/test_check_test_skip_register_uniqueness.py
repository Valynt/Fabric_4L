from pathlib import Path


def test_uniqueness_command_is_policy_free_delegate() -> None:
    source = Path("scripts/ci/check_test_skip_register_uniqueness.py").read_text(encoding="utf-8")
    assert "test_debt_governance_delegate import delegate" in source
    assert "find_duplicates" not in source
    assert "path_pattern + marker" not in source
