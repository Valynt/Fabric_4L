#!/usr/bin/env python3
"""Extract frontend route metadata from the React Router config."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ROUTER_PATH = Path("apps/web/src/shell/router.tsx")
OUTPUT_PATH = Path("apps/web/audit-output/track-a-route-extraction.json")
ROUTE_MAP_PATH = Path("apps/web/audit-output/route-map.md")


@dataclass
class RouteEntry:
    path: str
    component: str
    tier: str
    category: str
    redirect_target: str | None = None
    required_tier: str | None = None
    owner: str = "frontend-platform"


def extract_object_blocks(source: str) -> list[str]:
    blocks: list[str] = []
    for match in re.finditer(r"\{\s*path:\s*[\"']", source):
        start = match.start()
        depth = 0
        for idx in range(start, len(source)):
            char = source[idx]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(source[start : idx + 1])
                    break
    return blocks


def first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.DOTALL)
    return match.group(1) if match else None


def classify(block: str) -> tuple[str, str | None]:
    policy = first(r"accessPolicy:\s*([^}\n]+)", block) or ""
    if "requiresAuth: false" in block:
        return "public", None
    tier = first(r"requiredTier:\s*[\"']([^\"']+)[\"']", block)
    if not tier:
        tier = first(r"(tenant(?:Std|Adv|Admin)Policy|account(?:Std|Adv)Policy|homePolicy|authPolicy)", policy)
        tier = {
            "tenantStdPolicy": "standard",
            "accountStdPolicy": "standard",
            "tenantAdvPolicy": "advanced",
            "accountAdvPolicy": "advanced",
            "tenantAdminPolicy": "admin",
            "homePolicy": "authenticated",
            "authPolicy": "public",
        }.get(tier or "", None)
    if tier == "public":
        return "public", None
    return "authenticated", tier or "authenticated"


def component_name(block: str) -> tuple[str, str | None]:
    redirect = first(r"<Navigate\s+to=[\"']([^\"']+)[\"']", block)
    if redirect:
        return "Navigate", redirect
    component = first(r"<([A-Z][A-Za-z0-9_]*)\b", block)
    return component or "RouteElement", None


def main() -> int:
    content = ROUTER_PATH.read_text(encoding="utf-8")
    routes: list[RouteEntry] = []
    for block in extract_object_blocks(content):
        path = first(r"path:\s*[\"']([^\"']+)[\"']", block)
        if not path:
            continue
        component, redirect = component_name(block)
        category, tier = classify(block)
        if redirect:
            category = "redirect"
            tier = "redirect"
        routes.append(RouteEntry(path, component, tier or category, category, redirect, tier))

    seen: set[tuple[str, str]] = set()
    unique: list[RouteEntry] = []
    for route in routes:
        key = (route.path, route.component)
        if key not in seen:
            seen.add(key)
            unique.append(route)
    unique.sort(key=lambda r: (r.path == "*", r.path))

    summary = {
        "authenticated": sum(1 for r in unique if r.category == "authenticated"),
        "public": sum(1 for r in unique if r.category == "public"),
        "redirect": sum(1 for r in unique if r.category == "redirect"),
        "total": len(unique),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps({"summary": summary, "routes": [asdict(r) for r in unique]}, indent=2) + "\n", encoding="utf-8")

    lines = ["# Frontend Route Audit", "", f"**Total Routes:** {summary['total']}", ""]
    lines.append("| Path | Component | Category | Required tier | Owner |")
    lines.append("|---|---|---|---|---|")
    for route in unique:
        lines.append(f"| `{route.path}` | `{route.component}` | {route.category} | {route.required_tier or ''} | {route.owner} |")
    ROUTE_MAP_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("Route Extraction Summary")
    print("=" * 50)
    print(f"Authenticated routes: {summary['authenticated']}")
    print(f"Public routes: {summary['public']}")
    print(f"Redirect routes: {summary['redirect']}")
    print(f"Total: {summary['total']}")
    print(f"Routes saved to: {OUTPUT_PATH}")
    print(f"Route map saved to: {ROUTE_MAP_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
