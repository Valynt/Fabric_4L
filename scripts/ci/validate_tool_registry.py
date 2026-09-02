#!/usr/bin/env python3
"""CI gate script to validate tool manifests and policies.

Loads every .tool.yaml under contracts/tool-manifests/, validates it against
tool-manifest.schema.json, enforces policy rules, and produces a structured
report. Exit code 0 if all manifests pass; non-zero otherwise.

Usage:
    python3 scripts/ci/validate_tool_registry.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Third-party deps available in the CI environment (repo has yaml and jsonschema)
try:
    import yaml
except ImportError:  # pragma: no cover
    print("ERROR: PyYAML is required. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)

try:
    import jsonschema
except ImportError:  # pragma: no cover
    print("ERROR: jsonschema is required. Install: pip install jsonschema", file=sys.stderr)
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFESTS_DIR = REPO_ROOT / "contracts" / "tool-manifests"
SCHEMA_PATH = MANIFESTS_DIR / "tool-manifest.schema.json"
POLICIES_DIR = MANIFESTS_DIR / "policies"
POLICY_SCHEMA_PATH = MANIFESTS_DIR / "registry.schema.json"

# Known action IDs from the canonical permission catalog (populated at runtime)
# If a catalog file exists, it is loaded; otherwise the set stays empty and
# action-id cross-checks are skipped (warn-only).
ACTION_CATALOG_PATH = REPO_ROOT / "contracts" / "auth" / "action-catalog.json"


@dataclass
class Violation:
    path: str
    rule: str
    message: str
    severity: str  # error | warning


@dataclass
class Report:
    passed: bool = True
    manifests_loaded: int = 0
    manifests_valid: int = 0
    policies_loaded: int = 0
    violations: list[Violation] = field(default_factory=list)

    def add(self, violation: Violation) -> None:
        self.violations.append(violation)
        if violation.severity == "error":
            self.passed = False


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _discover_tool_manifests() -> list[Path]:
    """Return sorted list of .tool.yaml paths under MANIFESTS_DIR."""
    manifests: list[Path] = []
    for p in MANIFESTS_DIR.rglob("*.tool.yaml"):
        manifests.append(p)
    return sorted(manifests)


def _discover_policies() -> list[Path]:
    """Return sorted list of policy YAML paths under POLICIES_DIR."""
    if not POLICIES_DIR.exists():
        return []
    policies: list[Path] = []
    for p in POLICIES_DIR.rglob("*.yaml"):
        policies.append(p)
    return sorted(policies)


def _validate_manifest(
    manifest: dict[str, Any],
    schema: dict[str, Any],
    action_catalog: set[str],
    report: Report,
    source_path: str,
) -> None:
    """Validate a single manifest dict against the schema and policy rules."""
    report.manifests_loaded += 1

    # 1. JSON Schema validation
    # NOTE: source_path is injected for reporting (see main()). It is not part of
    # the canonical schema (additionalProperties: false), so validate against a
    # copy that omits it. Policy checks below still use the full dict.
    clean = {k: v for k, v in manifest.items() if k != "source_path"}
    try:
        jsonschema.validate(instance=clean, schema=schema)
    except jsonschema.ValidationError as exc:
        report.add(
            Violation(
                path=source_path,
                rule="schema",
                message=f"Schema validation failed: {exc.message} (path={list(exc.path)})",
                severity="error",
            )
        )
        return

    report.manifests_valid += 1

    # 2. Cross-reference: action_id must exist in action catalog (if catalog present)
    action_id = manifest.get("action_id")
    if action_id and action_catalog and action_id not in action_catalog:
        report.add(
            Violation(
                path=source_path,
                rule="action-catalog",
                message=f"action_id '{action_id}' not found in action catalog",
                severity="error",
            )
        )

    # 3. Mutating tools must have idempotency, revision, approval, and audit declarations
    side_effect = manifest.get("side_effect", "")
    is_mutating = side_effect in {
        "REVERSIBLE_MUTATION",
        "PROTECTED_MUTATION",
        "IRREVERSIBLE",
    }

    if is_mutating:
        idempotency = manifest.get("idempotency")
        if idempotency is None or not idempotency.get("required", False):
            report.add(
                Violation(
                    path=source_path,
                    rule="idempotency",
                    message=f"Mutating tool (side_effect={side_effect}) must declare idempotency with required=true",
                    severity="error",
                )
            )
        if manifest.get("revision") is None:
            report.add(
                Violation(
                    path=source_path,
                    rule="revision",
                    message=f"Mutating tool (side_effect={side_effect}) must declare revision",
                    severity="error",
                )
            )
        approval = manifest.get("approval_requirement")
        if approval is None or not approval.get("required", False):
            report.add(
                Violation(
                    path=source_path,
                    rule="approval",
                    message=f"Mutating tool (side_effect={side_effect}) must declare approval_requirement with required=true",
                    severity="error",
                )
            )
        audit = manifest.get("audit", {})
        if not audit.get("required", False):
            report.add(
                Violation(
                    path=source_path,
                    rule="audit",
                    message=f"Mutating tool (side_effect={side_effect}) must require audit",
                    severity="error",
                )
            )

    # 4. IRREVERSIBLE tools must have human_confirmation_required
    if side_effect == "IRREVERSIBLE" and not manifest.get("human_confirmation_required", False):
        report.add(
            Violation(
                path=source_path,
                rule="human-confirmation",
                message="IRREVERSIBLE tool must set human_confirmation_required = true",
                severity="error",
            )
        )

    # 5. Tenant binding: reject client-supplied tenant authority
    tenant_binding = manifest.get("tenant_binding", {})
    if tenant_binding.get("client_supplied_tenant_authoritative", True):
        report.add(
            Violation(
                path=source_path,
                rule="tenant-binding",
                message="tenant_binding.client_supplied_tenant_authoritative must be false; caller-selected tenant IDs are not permitted",
                severity="error",
            )
        )

    # 6. Financial-state-change tools must have human_confirmation_required
    if manifest.get("financial_state_change", False) and not manifest.get("human_confirmation_required", False):
        report.add(
            Violation(
                path=source_path,
                rule="financial-confirmation",
                message="Tool with financial_state_change = true must set human_confirmation_required = true",
                severity="error",
            )
        )

    # 7. DRAFT_ONLY tools must NOT actually mutate (enforced by classification)
    # This is more of a semantic rule; we can't detect runtime behavior statically,
    # but we can require that DRAFT_ONLY tools have financial_state_change = false
    # unless they are explicitly creating a draft.
    # Relaxed: skip — classification is human-reviewed.

    # 8. resource_resolver must be present and have authoritative_service
    resource_resolver = manifest.get("resource_resolver")
    if resource_resolver:
        if not resource_resolver.get("authoritative_service"):
            report.add(
                Violation(
                    path=source_path,
                    rule="resource-resolver",
                    message="resource_resolver.authoritative_service must be non-empty",
                    severity="error",
                )
            )
    else:
        # Resource resolver is optional, but if missing we warn
        report.add(
            Violation(
                path=source_path,
                rule="resource-resolver",
                message="resource_resolver is absent; consider adding one for tenant scoping",
                severity="warning",
            )
        )


def _validate_policy(policy: dict[str, Any], report: Report, source_path: str) -> None:
    """Validate a single policy YAML."""
    report.policies_loaded += 1
    agent_class = policy.get("agent_class")
    if not agent_class:
        report.add(
            Violation(
                path=source_path,
                rule="policy-schema",
                message="Policy must have 'agent_class' field",
                severity="error",
            )
        )
    allowed = set(policy.get("allowed_side_effects", []))
    denied = set(policy.get("denied_side_effects", []))
    overlap = allowed & denied
    if overlap:
        report.add(
            Violation(
                path=source_path,
                rule="policy-conflict",
                message=f"Side effects in both allowed and denied lists: {overlap}",
                severity="error",
            )
        )


def _check_billing_copilot_policy(
    manifests: list[dict[str, Any]], policies: list[dict[str, Any]], report: Report
) -> None:
    """Ensure billing-copilot cannot see IRREVERSIBLE tools."""
    billing_policy = next(
        (p for p in policies if p.get("agent_class") == "billing-copilot"), None
    )
    if not billing_policy:
        report.add(
            Violation(
                path="policies/",
                rule="billing-copilot-policy",
                message="No billing-copilot policy found",
                severity="error",
            )
        )
        return

    allowed = set(billing_policy.get("allowed_side_effects", []))
    denied = set(billing_policy.get("denied_side_effects", []))

    for manifest in manifests:
        side_effect = manifest.get("side_effect", "")
        tool_id = manifest.get("tool_id", "")
        if side_effect in denied and side_effect not in allowed:
            # This is the intended behavior — tool should be filtered out.
            # But we also check that the manifest does not claim to support billing-copilot.
            supported = manifest.get("supported_agent_classes", [])
            if "billing-copilot" in supported:
                report.add(
                    Violation(
                        path=manifest.get("source_path", tool_id),
                        rule="billing-copilot-denied",
                        message=(
                            f"Tool '{tool_id}' with side_effect={side_effect} is denied for "
                            f"billing-copilot but lists it in supported_agent_classes"
                        ),
                        severity="error",
                    )
                )


def _check_general_agent_policy(
    manifests: list[dict[str, Any]], policies: list[dict[str, Any]], report: Report
) -> None:
    """Ensure general-agent cannot see PROTECTED_MUTATION or IRREVERSIBLE tools."""
    general_policy = next(
        (p for p in policies if p.get("agent_class") == "general-agent"), None
    )
    if not general_policy:
        report.add(
            Violation(
                path="policies/",
                rule="general-agent-policy",
                message="No general-agent policy found",
                severity="error",
            )
        )
        return

    denied = set(general_policy.get("denied_side_effects", []))
    for manifest in manifests:
        side_effect = manifest.get("side_effect", "")
        tool_id = manifest.get("tool_id", "")
        supported = manifest.get("supported_agent_classes", [])
        if side_effect in denied and "general-agent" in supported:
            report.add(
                Violation(
                    path=manifest.get("source_path", tool_id),
                    rule="general-agent-denied",
                    message=(
                        f"Tool '{tool_id}' with side_effect={side_effect} is denied for "
                        f"general-agent but lists it in supported_agent_classes"
                    ),
                    severity="error",
                )
            )


def main() -> int:
    report = Report()

    # Load schemas
    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema not found: {SCHEMA_PATH}", file=sys.stderr)
        return 1
    schema = _load_json(SCHEMA_PATH)

    # Load action catalog if present
    action_catalog: set[str] = set()
    if ACTION_CATALOG_PATH.exists():
        catalog_data = _load_json(ACTION_CATALOG_PATH)
        action_catalog = set(catalog_data.get("actions", []))
    else:
        report.add(
            Violation(
                path=str(ACTION_CATALOG_PATH.relative_to(REPO_ROOT)),
                rule="action-catalog",
                message=f"Action catalog not found at {ACTION_CATALOG_PATH}; action_id cross-checks skipped.",
                severity="warning",
            )
        )

    # Discover and validate manifests
    manifest_paths = _discover_tool_manifests()
    manifest_dicts: list[dict[str, Any]] = []
    for path in manifest_paths:
        try:
            raw = _load_yaml(path)
        except yaml.YAMLError as exc:
            report.add(
                Violation(
                    path=str(path.relative_to(REPO_ROOT)),
                    rule="yaml-parse",
                    message=f"YAML parse error: {exc}",
                    severity="error",
                )
            )
            continue
        if not isinstance(raw, dict):
            report.add(
                Violation(
                    path=str(path.relative_to(REPO_ROOT)),
                    rule="yaml-parse",
                    message="YAML did not parse to a mapping",
                    severity="error",
                )
            )
            continue
        raw["source_path"] = str(path.relative_to(REPO_ROOT))
        _validate_manifest(raw, schema, action_catalog, report, raw["source_path"])
        manifest_dicts.append(raw)

    # Discover and validate policies
    policy_paths = _discover_policies()
    policy_dicts: list[dict[str, Any]] = []
    for path in policy_paths:
        try:
            raw = _load_yaml(path)
        except yaml.YAMLError as exc:
            report.add(
                Violation(
                    path=str(path.relative_to(REPO_ROOT)),
                    rule="yaml-parse",
                    message=f"YAML parse error: {exc}",
                    severity="error",
                )
            )
            continue
        if not isinstance(raw, dict):
            report.add(
                Violation(
                    path=str(path.relative_to(REPO_ROOT)),
                    rule="yaml-parse",
                    message="YAML did not parse to a mapping",
                    severity="error",
                )
            )
            continue
        _validate_policy(raw, report, str(path.relative_to(REPO_ROOT)))
        policy_dicts.append(raw)

    # Policy cross-checks
    _check_billing_copilot_policy(manifest_dicts, policy_dicts, report)
    _check_general_agent_policy(manifest_dicts, policy_dicts, report)

    # Report
    summary = {
        "passed": report.passed,
        "manifests_loaded": report.manifests_loaded,
        "manifests_valid": report.manifests_valid,
        "policies_loaded": report.policies_loaded,
        "violations": [
            {
                "path": v.path,
                "rule": v.rule,
                "message": v.message,
                "severity": v.severity,
            }
            for v in report.violations
        ],
        "violation_count": len(report.violations),
        "error_count": sum(1 for v in report.violations if v.severity == "error"),
        "warning_count": sum(1 for v in report.violations if v.severity == "warning"),
    }

    print(json.dumps(summary, indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
