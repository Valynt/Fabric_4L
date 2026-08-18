from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_contract_refresh_targets_are_phony() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    phony_declaration = makefile.split("\n\n", maxsplit=1)[0]

    for target in (
        "contracts",
        "validate-openapi-contracts",
        "contract-drift",
        "contract-freshness-fast",
        "contract-freshness",
    ):
        assert target in phony_declaration, (
            f"{target} must be phony so a same-named file or directory cannot "
            "silently skip contract validation"
        )
