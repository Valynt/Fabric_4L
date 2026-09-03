#!/usr/bin/env python3
"""Generate the Layer 4 Tool Registry Index from validated .tool.yaml manifests.

Reads all .tool.yaml files under contracts/tool-manifests/, produces:
  - contracts/tool-manifests/generated/layer4-tool-index.json
  - contracts/tool-manifests/generated/action-coverage.json

Usage:
    python3 scripts/ci/generate_tool_index.py

Exit code 0 on success, non-zero if validation fails.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFESTS_DIR = REPO_ROOT / "contracts" / "tool-manifests"
GENERATED_DIR = MANIFESTS_DIR / "generated"
INDEX_PATH = GENERATED_DIR / "layer4-tool-index.json"
COVERAGE_PATH = GENERATED_DIR / "action-coverage.json"
VALIDATOR_SCRIPT = REPO_ROOT / "scripts" / "ci" / "validate_tool_registry.py"


def _run_validator() -> tuple[bool, dict[str, Any]]:
    """Run the validator and return (success, parsed summary)."""
    result = subprocess.run(
        [sys.executable, str(VALIDATOR_SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    try:
        summary = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("ERROR: Validator produced invalid JSON:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return False, {}
    return summary.get("passed", False), summary


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _discover_manifests() -> list[Path]:
    return sorted(p for p in MANIFESTS_DIR.rglob("*.tool.yaml"))


def _load_policies() -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []
    policies_dir = MANIFESTS_DIR / "policies"
    if policies_dir.exists():
        for p in sorted(policies_dir.rglob("*.yaml")):
            policies.append(_load_yaml(p))
    return policies


def _build_agent_class_bindings(policies: list[dict[str, Any]]) -> dict[str, str]:
    """Map runtime agent identifiers to canonical agent classes."""
    # Default bindings: each agent class maps to itself
    bindings: dict[str, str] = {}
    for policy in policies:
        ac = policy.get("agent_class")
        if ac:
            bindings[ac] = ac
    # Add aliases if needed
    bindings["billing-copilot"] = "billing-copilot"
    bindings["general-agent"] = "general-agent"
    return bindings


def _build_policy_map(policies: list[dict[str, Any]]) -> dict[str, Any]:
    """Build policies dict keyed by agent_class."""
    out: dict[str, Any] = {}
    for policy in policies:
        ac = policy.get("agent_class")
        if not ac:
            continue
        out[ac] = {
            "allowed_side_effects": policy.get("allowed_side_effects", []),
            "denied_side_effects": policy.get("denied_side_effects", []),
            "allowed_tools": policy.get("allowed_tools", []),
            "denied_tools": policy.get("denied_tools", []),
            "require_human_confirmation_for_financial_tools": policy.get(
                "require_human_confirmation_for_financial_tools", False
            ),
            "description": policy.get("description", ""),
        }
    return out


def _compute_snapshot(manifests: list[Path]) -> tuple[str, str]:
    """Compute (snapshot_sha, registry_version) from manifest contents.

    ``snapshot_sha`` is the SHA-256 digest prefix of every source manifest.
    ``registry_version`` mirrors the loader's scheme: ``0.1.<patch>`` where the
    numeric patch component is derived from the same digest, so the CI generator
    and the runtime loader always emit an identical ``registry_version``.
    """
    hasher = hashlib.sha256()
    for p in manifests:
        hasher.update(p.read_bytes())
    snapshot_sha = hasher.hexdigest()[:16]
    patch = str(int(hasher.hexdigest()[:16], 16))[:10]
    registry_version = f"0.1.{patch}"
    return snapshot_sha, registry_version


def _git_generation_timestamp() -> str:
    """Deterministic generation timestamp in strict ISO 8601 (%cI).

    Derived from the most recent commit that touched the *input* sources
    (the manifests, policies, and schemas under ``contracts/tool-manifests``,
    excluding the ``generated/`` artifacts). Deriving from the input sources --
    rather than HEAD -- keeps the timestamp stable across later unrelated
    commits, so regenerating at any newer HEAD is a no-op and the CI drift
    check (``git diff --exit-code contracts/tool-manifests/generated``) does
    not race with the commit timestamp.

    Falls back to the current wall clock only when git metadata is unavailable
    (e.g. non-git checkouts), mirroring the loader's approach.
    """
    try:
        out = subprocess.run(
            [
                "git",
                "log",
                "-1",
                "--format=%cI",
                "--",
                str(MANIFESTS_DIR),
                f":!{GENERATED_DIR}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    # 1. Validate first
    passed, summary = _run_validator()
    if not passed:
        print("ERROR: Validation failed. Fix violations before generating index.", file=sys.stderr)
        print(json.dumps(summary, indent=2), file=sys.stderr)
        return 1

    # 2. Load manifests
    manifest_paths = _discover_manifests()
    manifests: list[dict[str, Any]] = []
    for path in manifest_paths:
        raw = _load_yaml(path)
        if not isinstance(raw, dict):
            continue
        # Build lightweight summary for the index
        summary_entry = {
            "tool_id": raw.get("tool_id"),
            "version": raw.get("version"),
            "status": raw.get("status"),
            "side_effect": raw.get("side_effect"),
            "action_id": raw.get("action_id"),
            "principal_types": raw.get("principal_types", []),
            "human_confirmation_required": raw.get("human_confirmation_required", False),
            "financial_state_change": raw.get("financial_state_change", False),
            "supported_agent_classes": raw.get("supported_agent_classes", []),
            "tenant_binding": raw.get("tenant_binding", {}),
            "source_path": path.relative_to(REPO_ROOT).as_posix(),
        }
        # Only include non-null fields for brevity
        summary_entry = {k: v for k, v in summary_entry.items() if v is not None}
        manifests.append(summary_entry)

    policies = _load_policies()
    policy_map = _build_policy_map(policies)
    agent_class_bindings = _build_agent_class_bindings(policies)

    # 3. Build index
    snapshot_version, registry_version = _compute_snapshot(manifest_paths)
    generated_at = _git_generation_timestamp()
    index = {
        "registry_version": registry_version,
        "generated_at": generated_at,
        "snapshot_sha": snapshot_version,
        "tool_manifests": manifests,
        "policies": policy_map,
        "agent_class_bindings": agent_class_bindings,
        "validation_report": {
            "passed": summary.get("passed", True),
            "violations": summary.get("error_count", 0),
            "manifests_loaded": summary.get("manifests_loaded", 0),
            "manifests_valid": summary.get("manifests_valid", 0),
        },
    }

    # 4. Build action coverage map
    action_coverage: dict[str, list[str]] = {}
    for raw in (_load_yaml(p) for p in manifest_paths):
        if not isinstance(raw, dict):
            continue
        action_id = raw.get("action_id")
        tool_id = raw.get("tool_id")
        if action_id and tool_id:
            action_coverage.setdefault(action_id, []).append(tool_id)

    coverage = {
        "generated_at": generated_at,
        "snapshot_sha": snapshot_version,
        "action_coverage": action_coverage,
        "uncovered_actions": [],  # To be populated if a canonical action catalog exists
    }

    # 5. Write generated files
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    with INDEX_PATH.open("w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)
        fh.write("\n")

    with COVERAGE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(coverage, fh, indent=2)
        fh.write("\n")

    print(f"Generated {INDEX_PATH.relative_to(REPO_ROOT)}")
    print(f"Generated {COVERAGE_PATH.relative_to(REPO_ROOT)}")
    print(f"Manifests: {len(manifests)}  Policies: {len(policies)}  Snapshot: {snapshot_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
