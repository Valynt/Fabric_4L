from pathlib import Path


def test_collection_command_is_subordinate_policy_free_delegate() -> None:
    source = Path("scripts/ci/check_pytest_skip_governance.py").read_text(encoding="utf-8")
    assert "delegate(collection_mode=True)" in source
    assert "allowlist" not in source
    assert "baseline" not in source
