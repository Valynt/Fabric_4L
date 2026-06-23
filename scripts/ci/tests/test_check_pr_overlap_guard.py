from scripts.ci.check_pr_overlap_guard import REQUIRED_SECTION, _has_required_section, evaluate


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
