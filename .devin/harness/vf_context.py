"""Value Fabric context assembler.

Builds a system prompt from canonical governance docs, scoped to the
layer(s) a task touches, within a token budget.
"""
import os
import sys
from pathlib import Path
from typing import List, Tuple

from vf_layer_router import detect_layers
from vf_memory import load_episodes

__all__ = ["build_vf_context", "MAX_CTX", "RESERVED", "BUDGET"]

ROOT = Path(__file__).parent.parent.parent
MAX_CTX = int(os.getenv("VF_HARNESS_MAX_CTX", "128000"))
RESERVED = int(os.getenv("VF_HARNESS_RESERVED", "40000"))
BUDGET = MAX_CTX - RESERVED

# Always-load governance docs, in priority order (must exist for a well-formed repo)
ALWAYS_LOAD = [
    ("AGENTS.md", 12000),
    ("canonical-paths-policy.md", 8000),
    ("contracts/GOVERNANCE.md", 6000),
]

# Layer-specific docs loaded only when task touches that layer.
# Paths are relative to repo root; missing files are silently skipped.
LAYER_DOCS = {
    1: [
        ("services/layer1-ingestion/README.md", 6000),
        ("value_fabric/layer1/__init__.py", 2000),
    ],
    2: [
        ("services/layer2-extraction/README.md", 6000),
        ("value_fabric/layer2/__init__.py", 2000),
    ],
    3: [
        ("services/layer3-knowledge/README.md", 6000),
        ("value_fabric/layer3/__init__.py", 2000),
    ],
    4: [
        ("value_fabric/layer4/__init__.py", 2000),
        ("layer4_agents/main.py", 4000),
    ],
    5: [
        ("services/layer5-ground-truth/README.md", 6000),
    ],
    6: [
        ("services/layer6-benchmarks/README.md", 6000),
        ("value_fabric/layer6/__init__.py", 2000),
    ],
}

# Contract docs loaded when API/schema/endpoint/hook/type work is detected
CONTRACT_DOCS = [
    ("contracts/frontend/01-api-boundary-contract.md", 6000),
    ("contracts/frontend/02-type-synchronization-contract.md", 6000),
    ("contracts/frontend/03-hook-architecture-contract.md", 6000),
]

# Permissions doc (safety-critical, always loaded last)
PERMISSIONS_DOC = ".agent/protocols/permissions.md"


def _token_estimate(text: str) -> int:
    """Rough chars-to-tokens estimate for budgeting."""
    return max(1, len(text) // 4)


def _read(rel_path: str, limit_chars: int | None = None) -> str:
    full = ROOT / rel_path
    if not full.exists():
        return ""
    try:
        content = full.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""
    return content[:limit_chars] if limit_chars else content


def _add_part(parts: List[str], used: int, header: str, text: str, budget: int) -> int:
    """Append a context part if it fits within the remaining budget.

    Returns the updated token count. If the part would exceed budget,
    it is silently skipped.
    """
    cost = _token_estimate(text)
    if used + cost > budget:
        return used
    parts.append(f"# {header}\n{text}")
    return used + cost


def build_vf_context(query: str, file_paths: List[str]) -> Tuple[str, int]:
    """Assemble a Value Fabric-specific system prompt within token budget.

    Returns (context_string, tokens_used).
    """
    parts: List[str] = []
    used = 0

    # --- Always-load governance docs (safety-critical, always included) ---
    for rel, limit in ALWAYS_LOAD:
        text = _read(rel, limit_chars=limit)
        if text:
            parts.append(f"# {rel}\n{text}")
            used += _token_estimate(text)

    # --- Layer detection ---
    layers, is_frontend = detect_layers(query, file_paths)

    # --- Layer-specific docs (skipped if budget exhausted) ---
    for layer in layers:
        for rel, limit in LAYER_DOCS.get(layer, []):
            text = _read(rel, limit_chars=limit)
            if text:
                used = _add_part(parts, used, f"Layer {layer} Context", text, BUDGET)

    # --- Frontend-specific governance ---
    if is_frontend:
        text = _read("DESIGN.md", limit_chars=10000)
        if text:
            used = _add_part(parts, used, "Frontend Governance (DESIGN.md)", text, BUDGET)

    # --- Contract docs if API/schema work is detected ---
    query_lower = query.lower()
    api_keywords = {"api", "contract", "schema", "endpoint", "hook", "type", "openapi", "route"}
    if any(k in query_lower for k in api_keywords):
        for rel, limit in CONTRACT_DOCS:
            text = _read(rel, limit_chars=limit)
            if text:
                used = _add_part(parts, used, "Contract Rules", text, BUDGET)

    # --- Recent episodic memory (layer-scoped) ---
    episodes = load_episodes(query, layers=layers, k=5)
    if episodes:
        used = _add_part(parts, used, "Recent Episodes", episodes, BUDGET)

    # --- Permissions / safety last (always included, even if it nudges over budget) ---
    perms = _read(PERMISSIONS_DOC, limit_chars=2000)
    if perms:
        parts.append(f"# Permissions\n{perms}")
        used += _token_estimate(perms)

    context = "\n\n---\n\n".join(parts)
    return context, used


def main():
    """CLI entry point: print assembled context for inspection."""
    query = os.environ.get("TASK", "")
    files_raw = os.environ.get("FILES", "")
    file_paths = [p.strip() for p in files_raw.split(",") if p.strip()]

    if not query:
        print("Usage: TASK='<query>' FILES='path1,path2' python vf_context.py")
        sys.exit(1)

    context, used = build_vf_context(query, file_paths)
    print(f"# Assembled Value Fabric Context ({used} estimated tokens)\n")
    print(context)


if __name__ == "__main__":
    main()
