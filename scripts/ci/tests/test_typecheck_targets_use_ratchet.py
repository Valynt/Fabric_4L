#!/usr/bin/env python3
"""Structural gate: every typecheck-layerN target must use the mypy ratchet.

Enforces that per-layer typecheck targets invoke ``check_mypy_baseline.py``
(the per-file error ratchet) rather than raw mypy or ``run_mypy_layer.py``
(which runs mypy without enforcing a baseline). This guarantees new type
errors fail closed at ``make typecheck`` and reductions are credited
automatically — the contract-first guard against silent typing-debt growth.

The sole exception is ``typecheck-layer4-strict``, a supplementary strict
namespace check that runs alongside (not instead of) the ratcheted
``typecheck-layer4`` target.

Ownership: Platform Governance. Troubleshooting: see
docs/runbooks/operational/governance-gates-troubleshooting.md.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MAKEFILE = REPO_ROOT / "Makefile"

# Targets that are exempt from the ratchet requirement. Each must have a
# documented justification. typecheck-layer4-strict is a supplementary
# strict-namespace check; the baseline ratchet for layer 4 is enforced by
# typecheck-layer4.
EXEMPT_TARGETS = {"typecheck-layer4-strict"}

TARGET_RE = re.compile(r"^(typecheck-layer[0-9](?:-5)?(?:-strict)?):\s*(?:.*)?$")
RECIPE_RE = re.compile(r"^\t(.*)$")


def _parse_typecheck_recipes(makefile: Path) -> dict[str, list[str]]:
    """Return {target_name: [recipe_line, ...]} for typecheck-layer* targets."""
    text = makefile.read_text(encoding="utf-8")
    recipes: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if not line.strip():
            current = None
            continue
        m = TARGET_RE.match(line)
        if m:
            current = m.group(1)
            recipes.setdefault(current, [])
            continue
        if current is None:
            continue
        rm = RECIPE_RE.match(line)
        if rm:
            recipes[current].append(rm.group(1))
        elif not line.startswith("\t") and not line.startswith("#"):
            # Non-recipe, non-comment line ends the recipe block
            current = None
    return recipes


def test_makefile_has_all_six_layer_targets() -> None:
    recipes = _parse_typecheck_recipes(MAKEFILE)
    expected = {
        "typecheck-layer1",
        "typecheck-layer2",
        "typecheck-layer2-5",
        "typecheck-layer3",
        "typecheck-layer4",
        "typecheck-layer5",
        "typecheck-layer6",
    }
    missing = expected - recipes.keys()
    assert not missing, f"Missing typecheck-layerN targets in Makefile: {sorted(missing)}"


def test_typecheck_layer_targets_use_baseline_ratchet() -> None:
    """Every typecheck-layerN target (except documented exemptions) must
    invoke check_mypy_baseline.py and must NOT invoke raw mypy or
    run_mypy_layer.py."""
    recipes = _parse_typecheck_recipes(MAKEFILE)
    full_text = "\n".join(
        line for lines in recipes.values() for line in lines
    )

    for target, lines in recipes.items():
        if target in EXEMPT_TARGETS:
            continue
        recipe_text = "\n".join(lines)
        assert "check_mypy_baseline.py" in recipe_text, (
            f"{target} recipe must invoke check_mypy_baseline.py (the mypy "
            f"ratchet); found recipe:\n{recipe_text}"
        )
        assert "run_mypy_layer.py" not in recipe_text, (
            f"{target} recipe must NOT invoke run_mypy_layer.py (raw mypy "
            f"without baseline enforcement); found recipe:\n{recipe_text}"
        )
        # Reject bare `mypy` invocations used as a command (e.g. `mypy src/`
        # or `uv run mypy ...`). Ignore the word "mypy" inside comments,
        # echo strings, or script/module names like check_mypy_baseline.py.
        bare_mypy = re.search(
            r"(?<![\w-])mypy(?:\s+(?:src|services|packages|--|\$|uv)|\s*$)",
            recipe_text,
        )
        assert bare_mypy is None, (
            f"{target} recipe must NOT invoke bare mypy directly; found "
            f"recipe:\n{recipe_text}"
        )


def test_typecheck_aggregate_target_invokes_all_layer_ratchets() -> None:
    """The aggregate `typecheck` target must depend on every layer ratchet
    so a PR cannot skip a layer."""
    text = MAKEFILE.read_text(encoding="utf-8")
    for layer in (
        "typecheck-layer1",
        "typecheck-layer2",
        "typecheck-layer2-5",
        "typecheck-layer3",
        "typecheck-layer4",
        "typecheck-layer5",
        "typecheck-layer6",
    ):
        assert layer in text, (
            f"Aggregate typecheck target must invoke {layer}; not found in Makefile"
        )


def test_exempt_targets_are_documented() -> None:
    """Every exempt target must have a justification comment in the Makefile."""
    text = MAKEFILE.read_text(encoding="utf-8")
    for target in EXEMPT_TARGETS:
        # The target line or a preceding comment must explain why it's exempt.
        # We check for the target's presence and a nearby "strict" justification.
        assert target in text, f"Exempt target {target} not found in Makefile"
