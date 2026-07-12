import subprocess
from unittest.mock import patch

from scripts.ci.check_pr_overlap_guard import REQUIRED_SECTION, _has_required_section, _merged_prs, evaluate


def test_evaluate_ignores_allowlisted_only_overlap() -> None:
    incoming = {"Makefile", "docs/reliability/dr-policy.md"}
    history = [(101, "ops updates", {"Makefile", "docs/reliability/dr-policy.md"})]

    flagged = evaluate(incoming, history, threshold=0.2)

    assert flagged == []


def test_evaluate_flags_runtime_overlap_even_with_allowlist_present() -> None:
    incoming = {
        "Makefile",
        "packages/shared/src/value_fabric/shared/runtime_guard.py",
        "packages/shared/src/value_fabric/shared/tenant.py",
    }
    history = [
        (
            77,
            "shared refactor",
            {
                "Makefile",
                "packages/shared/src/value_fabric/shared/runtime_guard.py",
                "packages/shared/src/value_fabric/shared/tenant.py",
            },
        )
    ]

    flagged = evaluate(incoming, history, threshold=0.5)

    assert len(flagged) == 1
    assert flagged[0].number == 77
    assert flagged[0].overlap_ratio == 1.0


def test_required_section_must_have_content() -> None:
    empty = f"## {REQUIRED_SECTION}\n\n"
    filled = f"## {REQUIRED_SECTION}\n\nTouches shared runtime to complete split migration.\n"

    assert _has_required_section(empty) is False
    assert _has_required_section(filled) is True


def test_merged_prs_excludes_current_and_limits_lookback() -> None:
    raw = [
        {"number": 939, "title": "nine-three-nine"},
        {"number": 938, "title": "current pr"},
        {"number": 937, "title": "nine-three-seven"},
        {"number": 936, "title": "nine-three-six"},
    ]

    with patch("scripts.ci.check_pr_overlap_guard._run_json", return_value=raw):
        result = _merged_prs("owner/repo", "main", lookback=2, exclude=938)

    assert result == [
        {"number": 939, "title": "nine-three-nine"},
        {"number": 937, "title": "nine-three-seven"},
    ]


def test_merged_prs_gracefully_degrades_on_gh_failure() -> None:
    error = subprocess.CalledProcessError(1, ["gh", "pr", "list"])

    with patch("scripts.ci.check_pr_overlap_guard._run_json", side_effect=error):
        result = _merged_prs("owner/repo", "main", lookback=5, exclude=1)

    assert result == []
