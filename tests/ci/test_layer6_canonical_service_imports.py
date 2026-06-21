"""ADR-027 Layer 6 import topology regression test.

Layer 6 runtime code is canonically imported through the ``layer6_benchmarks``
package under ``services/layer6-benchmarks/src``. The legacy
``value_fabric.layer6`` namespace must remain neutralized and must not extend
its namespace path into the service source tree.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LAYER6_SRC = REPO_ROOT / "services" / "layer6-benchmarks" / "src"


def test_shim_path_does_not_include_service_src() -> None:
    """value_fabric.layer6 must not include the service source tree in __path__."""
    import value_fabric.layer6

    assert not any("layer6-benchmarks" in str(p) for p in value_fabric.layer6.__path__)


def test_canonical_source_files_exist() -> None:
    """Canonical Layer 6 implementation files must exist in the service tree."""
    canonical_pkg = LAYER6_SRC / "layer6_benchmarks"

    assert (canonical_pkg / "api" / "main.py").exists()
    assert (canonical_pkg / "settings.py").exists()
    assert (canonical_pkg / "repositories" / "benchmark_repository.py").exists()
    assert (canonical_pkg / "metrics" / "prometheus_metrics.py").exists()


def test_shim_file_is_neutralized() -> None:
    """value_fabric/layer6/__init__.py must not contain path or runtime wiring."""
    shim = REPO_ROOT / "value_fabric" / "layer6" / "__init__.py"
    text = shim.read_text(encoding="utf-8")

    assert "__path__.append" not in text
    assert "__path__.insert" not in text
    assert "from layer6_benchmarks" not in text
    assert "import layer6_benchmarks" not in text
    assert "def " not in text
    assert "class " not in text


def test_canonical_service_import_uses_layer6_benchmarks_package() -> None:
    """Canonical Layer 6 modules import from the service package."""
    l6_src_str = str(LAYER6_SRC)
    if l6_src_str not in sys.path:
        sys.path.insert(0, l6_src_str)

    module = importlib.import_module("layer6_benchmarks.settings")

    assert hasattr(module, "Layer6Settings")

    import value_fabric.layer6

    assert not any(str(LAYER6_SRC) in str(p) for p in value_fabric.layer6.__path__)
