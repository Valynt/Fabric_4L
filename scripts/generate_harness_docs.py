#!/usr/bin/env python3
"""
generate_harness_docs.py

Validates and optionally regenerates harness documentation artifacts.

Modes:
  --check   Validate that all required docs exist and are internally consistent.
            Exits non-zero if any check fails. Used by `make docs-harness`.
  --fix     Regenerate auto-derivable sections (endpoint inventory, model list).
            Does not overwrite hand-written prose.

Checks performed:
  1. Required doc files exist.
  2. All FastAPI harness endpoints are listed in the architecture doc.
  3. All Pydantic API models are listed in the architecture doc.
  4. Runbook references the correct service port and base path.
  5. Config files exist and contain required top-level keys.
  6. TypeScript harness API client exports match Python endpoint count.

Usage:
  python3 scripts/generate_harness_docs.py --check
  python3 scripts/generate_harness_docs.py --fix
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent

HARNESS_ROUTES = REPO_ROOT / "services/layer4-agents/src/layer4_agents/api/routes/harness.py"
HARNESS_API_MODELS = REPO_ROOT / "services/layer4-agents/src/layer4_agents/harness/api_models.py"
HARNESS_RUNTIME_YAML = REPO_ROOT / "services/layer4-agents/config/harness.runtime.yaml"
HARNESS_SERVICE_YAML = REPO_ROOT / "services/layer4-agents/config/harness.service.yaml"
ARCH_DOC = REPO_ROOT / "docs/architecture/harness-agent-integration.md"
RUNBOOK = REPO_ROOT / "services/layer4-agents/docs/harness-runbook.md"
TS_API_CLIENT = REPO_ROOT / "apps/web/src/api/harness.ts"

REQUIRED_FILES = [
    HARNESS_ROUTES,
    HARNESS_API_MODELS,
    HARNESS_RUNTIME_YAML,
    HARNESS_SERVICE_YAML,
    ARCH_DOC,
    RUNBOOK,
    TS_API_CLIENT,
]

# Top-level keys that must appear in each YAML config file
RUNTIME_YAML_REQUIRED_KEYS = [
    "schema_version",
    "workflows",
]
# Workflow types that must appear under the `workflows:` block
RUNTIME_YAML_REQUIRED_WORKFLOWS = [
    "roi_calculator",
    "whitespace_analysis",
    "business_case",
    "orchestrator",
]
SERVICE_YAML_REQUIRED_KEYS = [
    "service",
    "database",
    "l5_integration",
    "observability",
    "security",
    "health",
]

# Expected service metadata in the runbook
EXPECTED_PORT = "8004"
EXPECTED_BASE_PATH = "/v1/harness"


# ── Extraction helpers ─────────────────────────────────────────────────────────


def extract_route_paths(routes_file: Path) -> list[str]:
    """Return all path strings from @router.{method}("...") decorators."""
    text = routes_file.read_text()
    # Match @router.get("/v1/harness/...") etc.
    return re.findall(r'@router\.\w+\(\s*["\']([^"\']+)["\']', text)


def extract_pydantic_models(models_file: Path) -> list[str]:
    """Return all top-level class names that inherit from BaseModel."""
    tree = ast.parse(models_file.read_text())
    models = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = [
                (b.id if isinstance(b, ast.Name) else getattr(b, "attr", ""))
                for b in node.bases
            ]
            if "BaseModel" in bases:
                models.append(node.name)
    return models


def extract_ts_exported_functions(ts_file: Path) -> list[str]:
    """Return function/arrow-function names exported from the TS harness client."""
    text = ts_file.read_text()
    # Match: export async function foo or export const foo = or  foo: async (
    names: list[str] = []
    names += re.findall(r"export\s+(?:async\s+)?function\s+(\w+)", text)
    names += re.findall(r"export\s+const\s+(\w+)\s*=", text)
    # Also capture keys inside harnessApi object literal
    names += re.findall(r"^\s{2,4}(\w+):\s*(?:async\s*)?\(", text, re.MULTILINE)
    return names


def yaml_top_level_keys(yaml_file: Path) -> list[str]:
    """Extract top-level YAML keys (no indentation) without a full YAML parser."""
    keys = []
    for line in yaml_file.read_text().splitlines():
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):", line)
        if m:
            keys.append(m.group(1))
    return keys


def yaml_second_level_keys(yaml_file: Path, parent_key: str) -> list[str]:
    """Extract keys nested one level under `parent_key:` in a YAML file."""
    keys = []
    in_parent = False
    for line in yaml_file.read_text().splitlines():
        # Detect the parent key at top level
        if re.match(rf"^{re.escape(parent_key)}:", line):
            in_parent = True
            continue
        if in_parent:
            # A new top-level key ends the parent block
            if re.match(r"^[a-zA-Z_]", line) and not line.startswith(" "):
                break
            # Two-space or four-space indented key
            m = re.match(r"^  ([a-zA-Z_][a-zA-Z0-9_]*):", line)
            if m:
                keys.append(m.group(1))
    return keys


# ── Checks ────────────────────────────────────────────────────────────────────


def check_required_files() -> list[str]:
    errors = []
    for f in REQUIRED_FILES:
        if not f.exists():
            errors.append(f"Missing required file: {f.relative_to(REPO_ROOT)}")
    return errors


def check_endpoints_in_arch_doc() -> list[str]:
    """Every route path should appear at least once in the architecture doc."""
    errors = []
    if not HARNESS_ROUTES.exists() or not ARCH_DOC.exists():
        return errors
    paths = extract_route_paths(HARNESS_ROUTES)
    arch_text = ARCH_DOC.read_text()
    for path in paths:
        # Strip path params for matching: /v1/harness/runs/{run_id} → runs
        slug = path.split("/")[-1].lstrip("{").rstrip("}")
        if slug not in arch_text and path not in arch_text:
            errors.append(
                f"Endpoint path not referenced in architecture doc: {path}"
            )
    return errors


def check_models_in_arch_doc() -> list[str]:
    """Key request/response models should appear in the architecture doc."""
    errors = []
    if not HARNESS_API_MODELS.exists() or not ARCH_DOC.exists():
        return errors
    models = extract_pydantic_models(HARNESS_API_MODELS)
    arch_text = ARCH_DOC.read_text()
    # Only check the most important models (request/response pairs)
    key_models = [m for m in models if m.endswith(("Request", "Response"))]
    for model in key_models:
        if model not in arch_text:
            errors.append(
                f"API model not referenced in architecture doc: {model}"
            )
    return errors


def check_runbook_metadata() -> list[str]:
    """Runbook must reference the correct port and base path."""
    errors = []
    if not RUNBOOK.exists():
        return errors
    text = RUNBOOK.read_text()
    if EXPECTED_PORT not in text:
        errors.append(
            f"Runbook does not reference expected service port {EXPECTED_PORT}"
        )
    if EXPECTED_BASE_PATH not in text:
        errors.append(
            f"Runbook does not reference expected base path {EXPECTED_BASE_PATH}"
        )
    return errors


def check_config_keys() -> list[str]:
    errors = []
    if HARNESS_RUNTIME_YAML.exists():
        top_keys = yaml_top_level_keys(HARNESS_RUNTIME_YAML)
        for required in RUNTIME_YAML_REQUIRED_KEYS:
            if required not in top_keys:
                errors.append(
                    f"harness.runtime.yaml missing top-level key: {required}"
                )
        # Check workflow types nested under `workflows:`
        workflow_keys = yaml_second_level_keys(HARNESS_RUNTIME_YAML, "workflows")
        for required in RUNTIME_YAML_REQUIRED_WORKFLOWS:
            if required not in workflow_keys:
                errors.append(
                    f"harness.runtime.yaml missing workflow type under 'workflows': {required}"
                )
    if HARNESS_SERVICE_YAML.exists():
        keys = yaml_top_level_keys(HARNESS_SERVICE_YAML)
        for required in SERVICE_YAML_REQUIRED_KEYS:
            if required not in keys:
                errors.append(
                    f"harness.service.yaml missing top-level key: {required}"
                )
    return errors


def check_ts_client_coverage() -> list[str]:
    """
    The TS client should expose at least as many operations as there are
    Python route handlers (rough parity check, not exact matching).
    """
    errors = []
    if not HARNESS_ROUTES.exists() or not TS_API_CLIENT.exists():
        return errors
    route_count = len(extract_route_paths(HARNESS_ROUTES))
    ts_fns = extract_ts_exported_functions(TS_API_CLIENT)
    # harnessApi object methods are the primary surface; allow some slack
    if len(ts_fns) < route_count - 2:
        errors.append(
            f"TypeScript harness client has {len(ts_fns)} exported operations "
            f"but Python routes define {route_count} endpoints. "
            f"Check apps/web/src/api/harness.ts for missing coverage."
        )
    return errors


# ── Fix mode ──────────────────────────────────────────────────────────────────


def generate_endpoint_inventory() -> str:
    """Produce a markdown table of all harness endpoints."""
    if not HARNESS_ROUTES.exists():
        return ""
    text = HARNESS_ROUTES.read_text()
    # Extract method + path pairs
    entries = re.findall(
        r'@router\.(\w+)\(\s*["\']([^"\']+)["\'].*?\)\s*\nasync def (\w+)',
        text,
        re.DOTALL,
    )
    if not entries:
        return ""
    lines = ["| Method | Path | Handler |", "|---|---|---|"]
    for method, path, handler in entries:
        lines.append(f"| `{method.upper()}` | `{path}` | `{handler}` |")
    return "\n".join(lines)


def generate_model_list() -> str:
    """Produce a markdown list of all Pydantic API models."""
    if not HARNESS_API_MODELS.exists():
        return ""
    models = extract_pydantic_models(HARNESS_API_MODELS)
    return "\n".join(f"- `{m}`" for m in sorted(models))


def run_fix() -> None:
    """Print auto-generated sections to stdout for manual insertion."""
    print("=== Endpoint Inventory (for architecture doc) ===\n")
    print(generate_endpoint_inventory())
    print("\n=== API Model List (for architecture doc) ===\n")
    print(generate_model_list())
    print(
        "\nNote: --fix prints generated content to stdout. "
        "Paste into the appropriate doc sections manually."
    )


# ── Main ──────────────────────────────────────────────────────────────────────


def run_checks() -> int:
    all_errors: list[str] = []

    checks = [
        ("Required files", check_required_files),
        ("Endpoints in architecture doc", check_endpoints_in_arch_doc),
        ("Models in architecture doc", check_models_in_arch_doc),
        ("Runbook metadata", check_runbook_metadata),
        ("Config file keys", check_config_keys),
        ("TypeScript client coverage", check_ts_client_coverage),
    ]

    for name, fn in checks:
        errors = fn()
        if errors:
            print(f"[FAIL] {name}:")
            for e in errors:
                print(f"       {e}")
            all_errors.extend(errors)
        else:
            print(f"[OK]   {name}")

    print()
    if all_errors:
        print(f"docs-harness: {len(all_errors)} check(s) failed.")
        return 1
    else:
        print("docs-harness: all checks passed.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate or regenerate harness documentation artifacts."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check",
        action="store_true",
        help="Validate docs. Exits non-zero on failure.",
    )
    group.add_argument(
        "--fix",
        action="store_true",
        help="Print auto-generated doc sections to stdout.",
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(run_checks())
    else:
        run_fix()


if __name__ == "__main__":
    main()
