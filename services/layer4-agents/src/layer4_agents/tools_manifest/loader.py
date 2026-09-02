"""Load and validate YAML tool manifests.

This module provides utilities for:
- Loading ``.tool.yaml`` files from the canonical ``contracts/tool-manifests/`` tree
- Validating them against the JSON Schema
- Compiling them into a ``ToolRegistryIndex``
- Filtering by policy (agent-type × side-effect)

Usage::

    from layer4_agents.tools_manifest import load_manifests
    index = load_manifests("contracts/tool-manifests")
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate

from .models import (
    RegistryValidationReport as RegistryValidationReportModel,
)
from .models import (
    ToolManifest,
    ToolManifestSummary,
    ToolRegistryIndex,
)

_REGISTRY_SCHEMA_NAME: str = "registry.schema.json"
_MANIFEST_SCHEMA_NAME: str = "tool-manifest.schema.json"


def _find_schema_path(manifests_dir: Path, schema_name: str) -> Path:
    candidate = manifests_dir / schema_name
    if candidate.exists():
        return candidate
    # Search upwards for contracts root
    for parent in manifests_dir.parents:
        candidate = parent / "contracts" / "tool-manifests" / schema_name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not locate {schema_name} relative to {manifests_dir}"
    )


def _load_json_schema(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return cast("dict[str, Any]", json.load(fh))


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return cast("dict[str, Any]", yaml.safe_load(fh))


def _git_sha(manifests_dir: Path) -> str:
    """Return the current git commit SHA for the repo containing *manifests_dir*."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=manifests_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"


def _manifest_paths(manifests_dir: Path) -> list[Path]:
    """Return all ``*.tool.yaml`` files under *manifests_dir*, sorted."""
    return sorted(manifests_dir.rglob("*.tool.yaml"))


class ToolValidationError(Exception):
    """Raised when a tool manifest fails validation."""

    def __init__(self, tool_id: str, violations: list[str]) -> None:
        self.tool_id = tool_id
        self.violations = violations
        super().__init__(
            f"Tool manifest '{tool_id}' has {len(violations)} violation(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class RegistryValidationReport:
    """Structured report from a registry validation run."""

    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: dict[str, list[str]] = {}
        self.warnings: dict[str, list[str]] = {}

    @property
    def valid(self) -> bool:
        return not self.failed

    def add_pass(self, tool_id: str) -> None:
        self.passed.append(tool_id)

    def add_fail(self, tool_id: str, violations: list[str]) -> None:
        self.failed[tool_id] = violations

    def add_warning(self, tool_id: str, warnings: list[str]) -> None:
        self.warnings.setdefault(tool_id, []).extend(warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "summary": {
                "total": len(self.passed) + len(self.failed),
                "passed": len(self.passed),
                "failed": len(self.failed),
            },
        }


def _check_caller_selected_tenant_authority(raw: dict[str, Any]) -> list[str]:
    """Reject manifests whose tenant binding trusts caller-selected tenant authority.

    The canonical JSON Schema encodes tenant isolation as
    ``tenant_binding.client_supplied_tenant_authoritative`` (and
    ``tenant_binding.resolve_server_side``). A value of ``True`` means the
    caller supplies the authoritative tenant ID, which violates the
    tenant-isolation invariant (tenant must come from authenticated context).
    """
    violations: list[str] = []
    binding = raw.get("tenant_binding")
    if isinstance(binding, dict):
        if binding.get("client_supplied_tenant_authoritative") is True:
            violations.append(
                "tenant_binding.client_supplied_tenant_authoritative must be false: "
                "tenant authority must come from authenticated context, not caller input."
            )
        if binding.get("resolve_server_side") is True and binding.get("client_supplied_tenant_authoritative") is True:
            violations.append(
                "tenant_binding.resolve_server_side cannot be true when "
                "tenant_binding.client_supplied_tenant_authoritative is true."
            )
    return violations


def validate_manifest(
    raw: dict[str, Any],
    manifest_schema: dict[str, Any],
    action_catalog: set[str] | None = None,
    strict: bool = True,
) -> list[str]:
    """Validate a single raw manifest dict.

    Returns a list of human-readable violation strings (empty if valid).
    """
    violations: list[str] = []

    # 1. JSON Schema structural validation
    try:
        validate(instance=raw, schema=manifest_schema)
    except JsonSchemaValidationError as exc:
        violations.append(f"JSON Schema validation error: {exc.message} at {list(exc.path)}")

    # 2. action_id cross-reference (if catalog supplied)
    action_id = raw.get("action_id")
    if action_catalog is not None and action_id not in action_catalog:
        violations.append(
            f"action_id '{action_id}' not found in the command/permission catalog."
        )

    # 3. Policy checks: every mutating tool needs idempotency, approval, and audit
    side_effect = raw.get("side_effect", "")
    mutating = side_effect in {
        "REVERSIBLE_MUTATION",
        "PROTECTED_MUTATION",
        "IRREVERSIBLE",
    }
    if mutating:
        idempotency = raw.get("idempotency", {})
        if not idempotency or idempotency.get("required") is not True:
            violations.append(
                "Mutating tool must declare idempotency.required = true."
            )
        approval = raw.get("approval_requirement", {})
        if not approval or approval.get("required") is not True:
            violations.append(
                "Mutating tool must declare 'approval_requirement' with required = true."
            )
        audit = raw.get("audit", {})
        if not audit or audit.get("required") is not True:
            violations.append(
                "Mutating tool must declare 'audit.required' = true."
            )

    # 4. Tenant isolation: reject caller-selected tenant authority
    violations.extend(_check_caller_selected_tenant_authority(raw))

    if strict:
        # 5. No IRREVERSIBLE tools for billing-copilot
        agent_classes = raw.get("supported_agent_classes", [])
        if "billing-copilot" in agent_classes and side_effect == "IRREVERSIBLE":
            violations.append(
                "Billing copilot must not be exposed to IRREVERSIBLE tools."
            )

    return violations


def _load_policies(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    """Load ``policies/*.yaml`` under *root* into Policy models + bindings.

    Returns ``(policies, agent_class_bindings)`` where ``policies`` is keyed by
    agent class name and ``bindings`` maps each agent class to its policy key.
    """
    from .models import AgentPolicy

    policies: dict[str, AgentPolicy] = {}
    bindings: dict[str, str] = {}
    policy_dir = root / "policies"
    if not policy_dir.exists():
        return policies, bindings
    for path in sorted(policy_dir.glob("*.yaml")):
        raw = _load_yaml(path)
        if not isinstance(raw, dict):
            continue
        agent_class = raw.get("agent_class")
        if not agent_class:
            continue
        policies[str(agent_class)] = AgentPolicy(
            allowed_side_effects=list(raw.get("allowed_side_effects", []) or []),
            allowed_tools=list(raw.get("allowed_tools", []) or []),
            denied_tools=list(raw.get("denied_tools", []) or []),
            denied_side_effects=list(raw.get("denied_side_effects", []) or []),
            require_human_confirmation_for_financial_tools=bool(
                raw.get("require_human_confirmation_for_financial_tools", False)
            ),
            description=raw.get("description"),
        )
        bindings[str(agent_class)] = str(agent_class)
    return policies, bindings


def load_manifests(
    manifests_dir: str | Path,
    *,
    manifest_schema: dict[str, Any] | None = None,
    registry_schema: dict[str, Any] | None = None,
    action_catalog: set[str] | None = None,
    strict: bool = True,
) -> tuple[ToolRegistryIndex, RegistryValidationReport]:
    """Load all ``*.tool.yaml`` files from *manifests_dir* and compile an index.

    Args:
        manifests_dir: Directory containing ``*.tool.yaml`` files.
        manifest_schema: Optional JSON Schema for a single manifest. If ``None``,
            the schema is located automatically under *manifests_dir*.
        registry_schema: Optional JSON Schema for the compiled registry index.
        action_catalog: Optional set of canonical action identifiers for
            cross-reference validation.
        strict: If ``True``, apply additional policy checks (e.g., billing
            copilot restrictions).

    Returns:
        A tuple of ``(ToolRegistryIndex, RegistryValidationReport)``.
        The index contains only manifests that passed validation.
        The report contains full pass/fail/warning details.
    """
    root = Path(manifests_dir).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Manifests directory not found: {root}")

    # Resolve schemas
    if manifest_schema is None:
        manifest_schema = _load_json_schema(_find_schema_path(root, _MANIFEST_SCHEMA_NAME))
    if registry_schema is None:
        registry_schema = _load_json_schema(_find_schema_path(root, _REGISTRY_SCHEMA_NAME))

    paths = _manifest_paths(root)
    report = RegistryValidationReport()
    valid_manifests: list[ToolManifest] = []
    valid_sources: list[Path] = []

    for path in paths:
        raw = _load_yaml(path)
        if not isinstance(raw, dict):
            report.add_fail(path.stem, ["YAML file did not parse to a mapping"])
            continue

        tool_id = raw.get("tool_id", path.stem)
        violations = validate_manifest(
            raw,
            manifest_schema,
            action_catalog=action_catalog,
            strict=strict,
        )

        if violations:
            report.add_fail(tool_id, violations)
            continue

        # Pydantic parse (catches type mismatches not caught by JSON Schema)
        try:
            manifest = ToolManifest.model_validate(raw)
        except Exception as exc:
            report.add_fail(tool_id, [f"Pydantic validation error: {exc}"])
            continue

        valid_manifests.append(manifest)
        valid_sources.append(path)
        report.add_pass(tool_id)

    # Build index
    ts = subprocess.run(
        ["git", "show", "-s", "--format=%ci", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    generated_at = ts.stdout.strip() if ts.returncode == 0 else ""
    if not generated_at:
        generated_at = datetime.now(UTC).isoformat()

    # Compute registry snapshot version from manifest hashes. The registry schema
    # requires registry_version to be strictly numeric (^[0-9]+\.[0-9]+\.[0-9]+$),
    # so derive a numeric patch component from the digest.
    hasher = hashlib.sha256()
    for m in valid_manifests:
        hasher.update(m.tool_id.encode())
    patch = str(int(hasher.hexdigest()[:16], 16))[:10]
    registry_version = f"0.1.{patch}"
    snapshot_sha = hasher.hexdigest()[:16]

    summaries = [
        ToolManifestSummary(
            tool_id=m.tool_id,
            version=m.version,
            status=m.status.value,
            side_effect=m.side_effect.value,
            action_id=m.action_id,
            principal_types=[p.value for p in m.principal_types],
            human_confirmation_required=m.human_confirmation_required,
            financial_state_change=m.financial_state_change,
            supported_agent_classes=m.supported_agent_classes,
            tenant_binding=m.tenant_binding,
            source_path=src.relative_to(root.parents[1]).as_posix(),
        )
        for m, src in zip(valid_manifests, valid_sources)
    ]

    policies, bindings = _load_policies(root)

    index = ToolRegistryIndex(
        registry_version=registry_version,
        generated_at=generated_at,
        snapshot_sha=snapshot_sha,
        tool_manifests=summaries,
        policies=policies,
        agent_class_bindings=bindings,
        validation_report=RegistryValidationReportModel(
            passed=report.valid,
            violations=sum(len(v) for v in report.failed.values()),
            manifests_loaded=len(paths),
            manifests_valid=len(valid_manifests),
        ),
    )

    # Validate the compiled index against registry schema
    try:
        index_dict = index.model_dump(mode="json")
        validate(instance=index_dict, schema=registry_schema)
    except JsonSchemaValidationError as exc:
        report.add_fail(
            "__registry__",
            [f"Compiled registry index failed schema validation: {exc.message}"],
        )

    return index, report


def filter_tools_for_agent(
    index: ToolRegistryIndex,
    agent_class: str,
) -> list[ToolManifestSummary]:
    """Filter the compiled registry index to the tools exposed to *agent_class*.

    Exposure is gated by the agent-class policy (allowed/denied side-effect
    classes and tool ids) and by each tool's ``supported_agent_classes``. A tool
    is exposed only when every gate permits it; anything not explicitly allowed
    fails closed.

    Args:
        index: The compiled registry index.
        agent_class: The agent class (e.g. ``"billing-copilot"``) requesting tools.

    Returns:
        The list of ``ToolManifestSummary`` objects the agent may discover.
    """
    policy = index.policies.get(agent_class)
    if policy is None:
        # Unknown agent class has no policy. Fail closed: expose nothing rather
        # than defaulting to an unrestricted view.
        return []

    allowed_side_effects = set(policy.allowed_side_effects)
    denied_side_effects = set(policy.denied_side_effects)
    allowed_tools = set(policy.allowed_tools)
    denied_tools = set(policy.denied_tools)

    requires_confirmation = policy.require_human_confirmation_for_financial_tools

    def _emit(manifest: ToolManifestSummary) -> ToolManifestSummary:
        # Fail closed: when the policy demands human confirmation for financial
        # state changes, force that requirement onto any exposed financial tool,
        # overriding an under-specified manifest default.
        if (
            requires_confirmation
            and manifest.financial_state_change
            and not manifest.human_confirmation_required
        ):
            return manifest.model_copy(update={"human_confirmation_required": True})
        return manifest

    exposed: list[ToolManifestSummary] = []
    for manifest in index.tool_manifests:
        # supported_agent_classes is an explicit allow-list when present.
        if manifest.supported_agent_classes and agent_class not in manifest.supported_agent_classes:
            continue
        # Explicit denials always win.
        if manifest.tool_id in denied_tools:
            continue
        if manifest.side_effect in denied_side_effects:
            continue
        # An explicit tool-id allowlist, when non-empty, grants access to the
        # listed tools regardless of their side-effect class.
        if allowed_tools:
            if manifest.tool_id in allowed_tools:
                exposed.append(_emit(manifest))
            continue
        # Attribute-based allow: the side-effect class must be explicitly
        # permitted. An empty allowlist therefore permits nothing (fail closed).
        if manifest.side_effect not in allowed_side_effects:
            continue
        exposed.append(_emit(manifest))
    return exposed
