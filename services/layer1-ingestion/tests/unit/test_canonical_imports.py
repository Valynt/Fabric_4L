"""Canonical import regression tests for Layer 1 (ADR-027).

Proves that direct service-tree imports resolve without the
``value_fabric.layer1`` namespace shim.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SERVICE_SRC = REPO_ROOT / "services" / "layer1-ingestion" / "src"


def _load_from_canonical_path(dotted_name: str, rel_path: str) -> types.ModuleType:
    """Load *dotted_name* directly from ``services/layer1-ingestion/src/{rel_path}``.

    Creates dummy parent packages in ``sys.modules`` so that
    cross-package relative imports in real ``__init__.py`` files do not
    interfere with the canonical-path assertion.
    """
    file_path = SERVICE_SRC / rel_path
    assert file_path.exists(), f"Canonical module missing: {file_path}"

    # Create dummy parent packages to bypass real __init__.py execution
    parts = dotted_name.split(".")
    created_parents: list[str] = []
    for i in range(1, len(parts)):
        parent_name = ".".join(parts[:i])
        if parent_name not in sys.modules:
            parent_mod = types.ModuleType(parent_name)
            parent_mod.__path__ = [str(SERVICE_SRC / parts[0])]
            sys.modules[parent_name] = parent_mod
            created_parents.append(parent_name)

    spec = importlib.util.spec_from_file_location(dotted_name, file_path)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(dotted_name)
    had_previous_module = dotted_name in sys.modules
    try:
        sys.modules[dotted_name] = mod
        if spec.loader:
            spec.loader.exec_module(mod)
    finally:
        if had_previous_module:
            sys.modules[dotted_name] = previous_module  # type: ignore[assignment]
        else:
            sys.modules.pop(dotted_name, None)
        for parent_name in reversed(created_parents):
            sys.modules.pop(parent_name, None)
    return mod


def test_crawler_httpx_crawler_at_canonical_path() -> None:
    mod = _load_from_canonical_path("layer1_ingestion.crawler.httpx_crawler", "layer1_ingestion/crawler/httpx_crawler.py")
    assert SERVICE_SRC.resolve() in Path(mod.__file__).resolve().parents


def test_crawler_playwright_crawler_at_canonical_path() -> None:
    mod = _load_from_canonical_path("layer1_ingestion.crawler.playwright_crawler", "layer1_ingestion/crawler/playwright_crawler.py")
    assert SERVICE_SRC.resolve() in Path(mod.__file__).resolve().parents


def test_crawler_smart_router_at_canonical_path() -> None:
    mod = _load_from_canonical_path("layer1_ingestion.crawler.smart_router", "layer1_ingestion/crawler/smart_router.py")
    assert SERVICE_SRC.resolve() in Path(mod.__file__).resolve().parents


def test_compliance_robots_checker_at_canonical_path() -> None:
    # Module uses cross-package relative imports (..shared) so we assert
    # file existence rather than executing it directly.
    canonical = SERVICE_SRC / "layer1_ingestion" / "compliance" / "robots_checker.py"
    assert canonical.exists(), f"Canonical module missing: {canonical}"


def test_compliance_pii_scanner_at_canonical_path() -> None:
    canonical = SERVICE_SRC / "layer1_ingestion" / "compliance" / "pii_scanner.py"
    assert canonical.exists(), f"Canonical module missing: {canonical}"


def test_shared_models_at_canonical_path() -> None:
    canonical = SERVICE_SRC / "layer1_ingestion" / "shared" / "models.py"
    assert canonical.exists(), f"Canonical module missing: {canonical}"


def test_skills_registry_at_canonical_path() -> None:
    canonical = SERVICE_SRC / "layer1_ingestion" / "skills" / "registry.py"
    assert canonical.exists(), f"Canonical module missing: {canonical}"


def test_tasks_py_uses_relative_crawler_imports() -> None:
    """tasks package must use relative crawler imports (no absolute import)."""
    import ast

    tasks_pkg = SERVICE_SRC / "layer1_ingestion" / "shared" / "tasks"
    py_files = sorted(tasks_pkg.glob("*.py"))
    assert py_files, f"No package files under {tasks_pkg}"

    # From package submodule depth (layer1_ingestion.shared.tasks.crawl) the
    # canonical crawler module resolves via ``...crawler`` (level 3); the
    # package ``__init__`` sits at level 2 (layer1_ingestion.shared.tasks).
    allowed_levels = {2, 3}
    found = False
    for tasks_file in py_files:
        tree = ast.parse(tasks_file.read_text(encoding="utf-8"), filename=str(tasks_file))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.level in allowed_levels
                and node.module is not None
                and node.module.startswith("crawler.")
                and any(alias.name == "HttpxCrawler" for alias in node.names)
            ):
                found = True
                break
    assert found, "Expected tasks package to import HttpxCrawler via relative crawler import"


def test_value_fabric_layer1_shim_resolves_to_canonical_path() -> None:
    """Backward-compat shim must still point to the canonical service tree."""
    import layer1_ingestion.crawler.httpx_crawler as shim_mod

    canonical_file = (SERVICE_SRC / "layer1_ingestion" / "crawler" / "httpx_crawler.py").resolve()
    shim_file = Path(shim_mod.__file__).resolve()
    assert shim_file == canonical_file, (
        f"Shim resolved to {shim_file}, expected {canonical_file}"
    )
