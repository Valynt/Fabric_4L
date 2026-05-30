"""ADR-027 Layer 4 import topology regression test.

Layer 4 runtime code is canonically imported through the restructured
``layer4_agents`` package under ``services/layer4-agents/src``. The legacy
``value_fabric.layer4`` shim must remain neutralized and must not extend its
namespace path into the service source tree.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER4_SRC = REPO_ROOT / "services" / "layer4-agents" / "src"


def test_shim_path_does_not_include_service_src() -> None:
    """value_fabric.layer4 shim is neutralized: __path__ must not include the service source tree."""
    import value_fabric.layer4

    assert not any("layer4-agents" in str(p) for p in value_fabric.layer4.__path__)


def test_canonical_source_files_exist() -> None:
    """Canonical Layer 4 implementation files must exist in the service tree."""
    canonical_pkg = LAYER4_SRC / "layer4_agents"

    assert (canonical_pkg / "tools" / "registry.py").exists()
    assert (canonical_pkg / "tools" / "knowledge.py").exists()
    assert (canonical_pkg / "api" / "routes" / "workflows.py").exists()
    assert (canonical_pkg / "metrics" / "llm_cost_calculator.py").exists()


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


def test_canonical_service_import_uses_restructured_package() -> None:
    """Canonical restructured Layer 4 module imports succeed from service src."""
    l4_src_str = str(LAYER4_SRC)
    if l4_src_str not in sys.path:
        sys.path.insert(0, l4_src_str)

    module = importlib.import_module("layer4_agents.startup.dependency_verifier")

    assert hasattr(module, "DependencyRule")

    import value_fabric.layer4

    assert not any(str(LAYER4_SRC) in str(p) for p in value_fabric.layer4.__path__)
