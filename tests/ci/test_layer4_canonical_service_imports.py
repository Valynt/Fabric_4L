"""ADR-027 Layer 4 import topology regression test.

Discovered constraint: Layer 4 source code uses relative imports
(e.g. ``from ..models.tool_schemas import ...``) that depend on the
``value_fabric.layer4`` namespace package hierarchy. Direct imports
from ``services/layer4-agents/src/`` fail with
``ImportError: attempted relative import beyond top-level package``.

Therefore, during the migration window, consumers must continue using
``value_fabric.layer4.*`` imports. True service-first direct imports
require restructuring the service package (e.g. adding a
``layer4_agents`` package root under ``src/``).

This test documents the current state and verifies the shim works.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER4_SRC = REPO_ROOT / "services" / "layer4-agents" / "src"


def test_shim_path_does_not_include_service_src() -> None:
    """value_fabric.layer4 shim is neutralized: __path__ must not include the service source tree."""
    import value_fabric.layer4

    assert not any("layer4-agents" in str(p) for p in value_fabric.layer4.__path__)


def test_canonical_source_files_exist() -> None:
    """Canonical Layer 4 implementation files must exist in the service tree."""
    assert (LAYER4_SRC / "tools" / "registry.py").exists()
    assert (LAYER4_SRC / "tools" / "knowledge.py").exists()
    assert (LAYER4_SRC / "api" / "routes" / "workflows.py").exists()
    assert (LAYER4_SRC / "metrics" / "llm_cost_calculator.py").exists()


def test_shim_file_is_neutralized() -> None:
    """value_fabric/layer4/__init__.py must be neutralized: no path manipulation."""
    shim = REPO_ROOT / "value_fabric" / "layer4" / "__init__.py"
    text = shim.read_text(encoding="utf-8")

    assert "__path__.append" not in text
    assert "__path__.insert" not in text
    # Must not contain function definitions, class definitions, or business logic
    assert "def " not in text
    assert "class " not in text


def test_no_production_runtime_imports_from_shim() -> None:
    """Production code in services/layer4-agents/src must not import services.layer4_agents.src.*"""
    import re

    prod_files = list(LAYER4_SRC.rglob("*.py"))
    violations = []
    import_pattern = re.compile(r"(^|\s)(from|import)\s+value_fabric\.layer4(\.|\s|$)")
    for path in prod_files:
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            # Skip comments and docstrings
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if import_pattern.search(line):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}:{i}: {line.strip()}")

    assert not violations, (
        "Production code should not import from its own namespace shim:\n"
        + "\n".join(violations)
    )


def test_direct_service_import_requires_package_restructuring() -> None:
    """Document known blocker: relative imports fail when src/ is on sys.path directly.

    When ``services/layer4-agents/src`` is added to ``sys.path`` and
    ``from tools.registry import ...`` is attempted, relative imports
    inside ``tools/calculation_tools.py`` like
    ``from ..models.tool_schemas import ...`` fail because ``tools``
    becomes a top-level package with no parent.

    Resolution: restructure ``src/*`` into ``src/layer4_agents/*``
    so the service is a proper Python package.
    """
    l4_src_str = str(LAYER4_SRC)
    if l4_src_str not in sys.path:
        sys.path.insert(0, l4_src_str)

    # This will fail until the package is restructured
    try:
        from tools.registry import ToolRegistry  # noqa: F401
    except ImportError as exc:
        assert "relative import beyond top-level" in str(exc) or "attempted relative import" in str(exc)
    else:
        pytest.fail("Expected ImportError for direct service import before restructuring")
