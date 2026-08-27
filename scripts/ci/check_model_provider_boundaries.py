#!/usr/bin/env python3
"""Block new direct model-provider access outside the migration allowlist.

This is a strangler-pattern ratchet. The allowlist records direct access that
exists before the unified model gateway migration. Existing entries may be
removed, but new entries must not be added merely to make this check pass.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOTS = (REPO_ROOT / "services", REPO_ROOT / "packages")

PROVIDER_MODULES = frozenset({"openai", "anthropic", "together", "thesys"})
PROVIDER_HOSTS = (
    "api.openai.com",
    "api.anthropic.com",
    "api.together.ai",
    "api.thesys.dev",
)

# P0 baseline. Shrink this set as P1/P2 callers move behind fabric_model_gateway.
LEGACY_DIRECT_ACCESS = frozenset(
    {
        "services/layer2-extraction/src/layer2_extraction/shared/llm_client.py",
        "services/layer4-agents/src/layer4_agents/api/routes/c1.py",
        "services/layer4-agents/src/layer4_agents/config/settings.py",
        "services/layer4-agents/src/layer4_agents/services/anthropic_provider.py",
        "services/layer4-agents/src/layer4_agents/services/conversation.py",
        "services/layer4-agents/src/layer4_agents/services/llm_provider.py",
        "services/layer4-agents/src/layer4_agents/services/together_provider.py",
    }
)


def _imports_provider(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".", 1)[0] in PROVIDER_MODULES for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".", 1)[0] in PROVIDER_MODULES:
                return True
    return False


def find_direct_provider_access(repo_root: Path = REPO_ROOT) -> set[str]:
    """Return runtime files that import provider SDKs or name provider hosts."""
    found: set[str] = set()
    for root_name in ("services", "packages"):
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            relative_parts = path.relative_to(repo_root).parts
            if any(
                part in {"tests", "test", "__pycache__", "site-packages"}
                or part.startswith(".")
                for part in relative_parts
            ):
                continue
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source, filename=str(path))
            except (OSError, SyntaxError, UnicodeError):
                continue
            if _imports_provider(tree) or any(host in source for host in PROVIDER_HOSTS):
                found.add(path.relative_to(repo_root).as_posix())
    return found


def main() -> int:
    found = find_direct_provider_access()
    violations = sorted(found - LEGACY_DIRECT_ACCESS)
    stale = sorted(LEGACY_DIRECT_ACCESS - found)

    if stale:
        print("Model-provider boundary allowlist has stale entries; remove them:")
        for path in stale:
            print(f"  - {path}")
        return 1

    if violations:
        print("Direct model-provider access is prohibited outside the gateway baseline:")
        for path in violations:
            print(f"  - {path}")
        print("Route the call through the governed gateway; do not expand the allowlist.")
        return 1

    print(f"Model-provider boundary ratchet passed ({len(found)} legacy paths tracked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
