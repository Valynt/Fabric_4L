"""Prevent provider SDK imports inside Layer 4 orchestration modules."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATION_MODULES = [
    ROOT / "services/layer4-agents/src/engine",
    ROOT / "services/layer4-agents/src/workflows",
    ROOT / "services/layer4-agents/src/services/enrichment_orchestrator.py",
    ROOT / "services/layer4-agents/src/services/intelligence_orchestrator.py",
    ROOT / "services/layer4-agents/src/services/conversation.py",
]
BLOCKED_IMPORTS = ("openai", "anthropic", "together")


def _iter_py_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.py"))


def test_orchestration_modules_do_not_import_provider_sdks_directly() -> None:
    violations: list[str] = []
    for module_path in ORCHESTRATION_MODULES:
        for file_path in _iter_py_files(module_path):
            tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [n.name for n in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    if any(name == blocked or name.startswith(f"{blocked}.") for blocked in BLOCKED_IMPORTS):
                        violations.append(f"{file_path.relative_to(ROOT)} imports {name}")
    assert not violations, "\n".join(violations)
