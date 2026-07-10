#!/usr/bin/env python3
"""Validate Layer 4 agent-registry contract metadata.

Phase 1 of the architectural-drift program records Layer 4 semantic
contracts under ``contracts/agent-registry`` before runtime enforcement is
introduced. This script is intentionally lightweight and dependency-free so it
can run in the existing contract CI gate.

The validator fails for malformed registry documents and missing mandatory
contract metadata. Cross-checks against Layer 4 source configuration are emitted
as warnings by default because the approved rollout starts in warning mode.
Set ``AGENT_REGISTRY_STRICT=1`` or pass ``--strict`` to make warnings blocking.

Usage:
    python scripts/ci/check_agent_registry.py
    python scripts/ci/check_agent_registry.py contracts/agent-registry --strict
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_ROOT = REPO_ROOT / "contracts" / "agent-registry"
TOOL_MANIFEST_ROOT = REPO_ROOT / "contracts" / "tool-manifests"
AGENT_TAXONOMY_PATH = REPO_ROOT / "services" / "layer4-agents" / "src" / "agents" / "taxonomy.py"
WORKFLOW_CONFIG_PATH = REPO_ROOT / "services" / "layer4-agents" / "src" / "models" / "workflow_config.py"
MODEL_REGISTRY_SERVICE_PATH = REPO_ROOT / "services" / "layer4-agents" / "src" / "registry" / "service.py"
MODEL_REGISTRY_ROUTES_PATH = REPO_ROOT / "services" / "layer4-agents" / "src" / "registry" / "api" / "routes.py"
L4_SETTINGS_PATH = REPO_ROOT / "services" / "layer4-agents" / "src" / "config" / "settings.py"
ALLOWED_MODEL_STAGES = {"dev", "staging", "production", "deprecated"}

BASE_REQUIRED_FIELDS = {
    "id",
    "version",
    "kind",
    "owner",
    "risk_class",
    "description",
    "compatibility",
    "observability",
    "governance",
}
ALLOWED_KINDS = {
    "agent_output",
    "prompt",
    "tool",
    "workflow",
    "memory_object",
    "reasoning_policy",
    "semantic_compatibility",
}
ALLOWED_RISK_CLASSES = {"low", "medium", "high", "regulated"}
SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


@dataclass(frozen=True)
class Finding:
    """A registry validation finding."""

    severity: str
    path: Path
    rule: str
    message: str


class RegistryValidator:
    """Validates agent-registry documents and source coverage."""

    def __init__(self, registry_root: Path, strict: bool) -> None:
        self.registry_root = registry_root
        self.strict = strict
        self.errors: list[Finding] = []
        self.warnings: list[Finding] = []
        self.documents: dict[Path, dict[str, Any]] = {}

    def validate(self) -> int:
        """Run all registry validation checks."""
        if not self.registry_root.exists():
            self._error(self.registry_root, "registry-missing", "Agent registry directory does not exist")
            return self._report()

        self._load_json_documents()
        self._validate_required_layout()
        self._validate_base_metadata()
        self._validate_agent_manifest()
        self._validate_tool_manifest()
        self._validate_workflows()
        self._validate_prompts()
        self._validate_reasoning_policies()
        self._validate_semantic_compatibility_matrix()
        self._validate_model_registry_runtime_alignment()
        return self._report()

    def _load_json_documents(self) -> None:
        for path in sorted(self.registry_root.rglob("*.json")):
            try:
                self.documents[path] = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                self._error(path, "invalid-json", f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")

    def _validate_required_layout(self) -> None:
        required_files = [
            "README.md",
            "agents/manifest.json",
            "tools/manifest.json",
            "schemas/agent-output.schema.json",
            "schemas/base-contract.schema.json",
            "schemas/prompt.schema.json",
            "schemas/reasoning-policy.schema.json",
            "schemas/tool-error.schema.json",
            "schemas/tool-registry.schema.json",
            "schemas/workflow.schema.json",
            "schemas/semantic-compatibility.schema.json",
            "compatibility-matrix.json",
        ]
        for relative_path in required_files:
            path = self.registry_root / relative_path
            if not path.exists():
                self._error(path, "required-file-missing", f"Required registry file is missing: {relative_path}")

        for directory in ("prompts", "reasoning-policies", "workflows"):
            dir_path = self.registry_root / directory
            if not dir_path.exists() or not any(dir_path.glob("*.json")):
                self._error(dir_path, "required-entry-missing", f"Registry directory must contain at least one JSON contract: {directory}")

    def _validate_base_metadata(self) -> None:
        for path, document in self.documents.items():
            if "/schemas/" in path.as_posix():
                continue

            missing = sorted(BASE_REQUIRED_FIELDS - set(document))
            if missing:
                self._error(path, "base-metadata-missing", f"Missing required contract metadata: {', '.join(missing)}")

            kind = document.get("kind")
            if kind not in ALLOWED_KINDS:
                self._error(path, "invalid-kind", f"Invalid contract kind: {kind!r}")

            risk_class = document.get("risk_class")
            if risk_class not in ALLOWED_RISK_CLASSES:
                self._error(path, "invalid-risk-class", f"Invalid risk_class: {risk_class!r}")

            version = document.get("version")
            if not isinstance(version, str) or not SEMVER_RE.match(version):
                self._error(path, "invalid-version", f"Version must use semver MAJOR.MINOR.PATCH: {version!r}")

            for section in ("compatibility", "observability", "governance"):
                if section in document and not isinstance(document[section], dict):
                    self._error(path, "invalid-governance-section", f"{section} must be an object")

    def _validate_agent_manifest(self) -> None:
        path = self.registry_root / "agents" / "manifest.json"
        document = self.documents.get(path)
        if document is None:
            return

        agents = document.get("agents")
        if not isinstance(agents, list) or not agents:
            self._error(path, "agent-list-missing", "Agent manifest must contain a non-empty agents array")
            return

        seen: set[str] = set()
        registered_agent_types: set[str] = set()
        for index, agent in enumerate(agents):
            if not isinstance(agent, dict):
                self._error(path, "invalid-agent-entry", f"agents[{index}] must be an object")
                continue

            agent_type = agent.get("agent_type")
            if not isinstance(agent_type, str) or not agent_type:
                self._error(path, "agent-type-missing", f"agents[{index}] is missing agent_type")
                continue
            if agent_type in seen:
                self._error(path, "duplicate-agent-type", f"Duplicate agent_type: {agent_type}")
            seen.add(agent_type)
            registered_agent_types.add(agent_type)

            source_path = agent.get("source_path")
            if not isinstance(source_path, str) or not source_path:
                self._error(path, "agent-source-path-missing", f"{agent_type} is missing source_path")
            elif not (REPO_ROOT / source_path).exists():
                self._error(path, "agent-source-path-invalid", f"{agent_type} source_path does not exist: {source_path}")

            capabilities = agent.get("capabilities")
            if not isinstance(capabilities, list) or not capabilities or not all(isinstance(item, str) and item for item in capabilities):
                self._error(path, "agent-capabilities-invalid", f"{agent_type} must declare one or more string capabilities")

            envelope = agent.get("decision_envelope")
            if not isinstance(envelope, dict):
                self._error(path, "agent-envelope-missing", f"{agent_type} is missing decision_envelope")
                continue

            for section in ("input_schema", "output_schema", "error_schema"):
                if section not in envelope:
                    self._error(path, "agent-envelope-section-missing", f"{agent_type} decision_envelope missing {section}")

            required_context = envelope.get("required_context_fields")
            if not isinstance(required_context, list):
                self._error(path, "agent-context-fields-invalid", f"{agent_type} required_context_fields must be a list")
            else:
                for field in ("tenant_id", "trace_id"):
                    if field not in required_context:
                        self._error(path, "agent-context-field-missing", f"{agent_type} must require context field {field}")

        canonical_agent_types = self._canonical_agent_types()
        missing = sorted(canonical_agent_types - registered_agent_types)
        extra = sorted(registered_agent_types - canonical_agent_types)
        if missing:
            self._warning(path, "canonical-agent-missing", f"AgentType enum entries missing from registry: {', '.join(missing)}")
        if extra:
            self._warning(path, "unknown-agent-registered", f"Registry entries not present in AgentType enum: {', '.join(extra)}")

    def _validate_tool_manifest(self) -> None:
        path = self.registry_root / "tools" / "manifest.json"
        document = self.documents.get(path)
        if document is None:
            return

        tools = document.get("tools")
        if not isinstance(tools, list) or not tools:
            self._error(path, "tool-list-missing", "Tool registry must contain a non-empty tools array")
            return

        registered_names: set[str] = set()
        for index, tool in enumerate(tools):
            if not isinstance(tool, dict):
                self._error(path, "invalid-tool-entry", f"tools[{index}] must be an object")
                continue

            name = tool.get("name")
            if not isinstance(name, str) or not name:
                self._error(path, "tool-name-missing", f"tools[{index}] is missing name")
                continue
            if name in registered_names:
                self._error(path, "duplicate-tool", f"Duplicate tool registry entry: {name}")
            registered_names.add(name)

            manifest_path = tool.get("manifest_path")
            if not isinstance(manifest_path, str) or not manifest_path:
                self._error(path, "tool-manifest-path-missing", f"{name} is missing manifest_path")
                continue
            resolved_manifest = (path.parent / manifest_path).resolve()
            if not resolved_manifest.exists():
                self._error(path, "tool-manifest-path-invalid", f"{name} manifest_path does not exist: {manifest_path}")

            if tool.get("tenant_required") is not True:
                self._error(path, "tool-tenant-required", f"{name} must set tenant_required=true")

            provenance = tool.get("provenance")
            if not isinstance(provenance, dict) or provenance.get("required") is not True:
                self._error(path, "tool-provenance-required", f"{name} must require provenance")
            else:
                fields = provenance.get("fields")
                if not isinstance(fields, list):
                    self._error(path, "tool-provenance-fields-invalid", f"{name} provenance.fields must be a list")
                else:
                    for field in ("tenant_id", "trace_id", "tool_name", "tool_version", "caller_agent_type"):
                        if field not in fields:
                            self._error(path, "tool-provenance-field-missing", f"{name} provenance missing {field}")

        expected_tool_names = {tool_path.stem for tool_path in TOOL_MANIFEST_ROOT.glob("*.json")}
        missing = sorted(expected_tool_names - registered_names)
        extra = sorted(registered_names - expected_tool_names)
        if missing:
            self._warning(path, "tool-manifest-unregistered", f"Tool manifests missing from registry: {', '.join(missing)}")
        if extra:
            self._warning(path, "tool-registry-extra", f"Tool registry entries without a source manifest: {', '.join(extra)}")

    def _validate_workflows(self) -> None:
        workflow_paths = sorted((self.registry_root / "workflows").glob("*.json"))
        registered_workflows: set[str] = set()
        for path in workflow_paths:
            document = self.documents.get(path)
            if document is None:
                continue

            if document.get("kind") != "workflow":
                self._error(path, "workflow-kind-invalid", "Workflow registry entries must use kind=workflow")

            workflow_type = document.get("workflow_type")
            if not isinstance(workflow_type, str) or not workflow_type:
                self._error(path, "workflow-type-missing", "Workflow registry entry missing workflow_type")
                continue
            registered_workflows.add(workflow_type)

            source_path = document.get("source_path")
            if not isinstance(source_path, str) or not source_path:
                self._error(path, "workflow-source-path-missing", f"{workflow_type} is missing source_path")
            elif not (path.parent / source_path).resolve().exists():
                self._error(path, "workflow-source-path-invalid", f"{workflow_type} source_path does not exist: {source_path}")

            states = document.get("states")
            if not isinstance(states, list) or not states:
                self._error(path, "workflow-states-invalid", f"{workflow_type} must declare non-empty states")
                continue

            entry_point = document.get("entry_point")
            if entry_point not in states:
                self._error(path, "workflow-entry-point-invalid", f"{workflow_type} entry_point must be present in states")

            state_set = set(states)
            transitions = document.get("transitions")
            if not isinstance(transitions, list):
                self._error(path, "workflow-transitions-invalid", f"{workflow_type} transitions must be a list")
            else:
                for index, transition in enumerate(transitions):
                    if not isinstance(transition, dict):
                        self._error(path, "workflow-transition-invalid", f"{workflow_type} transitions[{index}] must be an object")
                        continue
                    for endpoint in ("source", "target"):
                        value = transition.get(endpoint)
                        if value not in state_set:
                            self._error(path, "workflow-transition-unknown-state", f"{workflow_type} transition {index} {endpoint} references unknown state {value!r}")

        canonical_workflows = self._canonical_workflow_types()
        missing = sorted(canonical_workflows - registered_workflows)
        extra = sorted(registered_workflows - canonical_workflows)
        if missing:
            self._warning(self.registry_root / "workflows", "workflow-config-unregistered", f"Workflow configs missing from registry: {', '.join(missing)}")
        if extra:
            self._warning(self.registry_root / "workflows", "workflow-registry-extra", f"Workflow registry entries without source config: {', '.join(extra)}")

    def _validate_prompts(self) -> None:
        for path in sorted((self.registry_root / "prompts").glob("*.json")):
            document = self.documents.get(path)
            if document is None:
                continue
            if document.get("kind") != "prompt":
                self._error(path, "prompt-kind-invalid", "Prompt registry entries must use kind=prompt")
            for field in ("prompt_path", "inputs", "outputs", "reasoning_policy", "changelog"):
                if field not in document:
                    self._error(path, "prompt-field-missing", f"Prompt registry entry missing {field}")
            self._validate_relative_file_reference(path, document, "prompt_path")
            if not isinstance(document.get("inputs"), list) or not document.get("inputs"):
                self._error(path, "prompt-inputs-missing", "Prompt registry entry must declare non-empty inputs")
            if not isinstance(document.get("outputs"), list) or not document.get("outputs"):
                self._error(path, "prompt-outputs-missing", "Prompt registry entry must declare non-empty outputs")
            if not isinstance(document.get("changelog"), list) or not document.get("changelog"):
                self._error(path, "prompt-changelog-missing", "Prompt registry entry must include a non-empty changelog")

    def _validate_reasoning_policies(self) -> None:
        for path in sorted((self.registry_root / "reasoning-policies").glob("*.json")):
            document = self.documents.get(path)
            if document is None:
                continue
            if document.get("kind") != "reasoning_policy":
                self._error(path, "reasoning-policy-kind-invalid", "Reasoning policies must use kind=reasoning_policy")
            for field in (
                "confidence_thresholds",
                "evidence_requirements",
                "explanation_requirements",
                "escalation_rules",
                "allowed_tool_classes",
            ):
                if field not in document:
                    self._error(path, "reasoning-policy-field-missing", f"Reasoning policy missing {field}")
            if not isinstance(document.get("confidence_thresholds"), dict) or not document.get("confidence_thresholds"):
                self._error(path, "reasoning-policy-thresholds-missing", "Reasoning policy must declare confidence_thresholds")
            for field in ("evidence_requirements", "explanation_requirements", "escalation_rules", "allowed_tool_classes"):
                if not isinstance(document.get(field), list) or not document.get(field):
                    self._error(path, "reasoning-policy-list-missing", f"Reasoning policy must declare non-empty {field}")

    def _validate_semantic_compatibility_matrix(self) -> None:
        """Validate the Phase 2 semantic-contract compatibility matrix."""

        path = self.registry_root / "compatibility-matrix.json"
        document = self.documents.get(path)
        if document is None:
            return

        required_fields = {
            "id",
            "version",
            "agent_registry_version",
            "min_runtime_version",
            "enforcement_default",
            "compatible_event_versions",
            "agent_contracts",
            "prompt_contracts",
            "tool_contracts",
            "workflow_contracts",
            "memory_contracts",
            "deprecated_contracts",
        }
        missing = sorted(required_fields - set(document))
        if missing:
            self._error(path, "semantic-compatibility-field-missing", f"Compatibility matrix missing fields: {', '.join(missing)}")

        for field in ("version", "agent_registry_version"):
            value = document.get(field)
            if not isinstance(value, str) or not SEMVER_RE.match(value):
                self._error(path, "semantic-compatibility-version-invalid", f"{field} must use semver MAJOR.MINOR.PATCH: {value!r}")

        if document.get("enforcement_default") not in {"warn", "strict"}:
            self._error(path, "semantic-compatibility-enforcement-invalid", "enforcement_default must be warn or strict")

        for section in (
            "compatible_event_versions",
            "agent_contracts",
            "prompt_contracts",
            "tool_contracts",
            "workflow_contracts",
            "memory_contracts",
        ):
            contracts = document.get(section)
            if not isinstance(contracts, dict) or not contracts:
                self._error(path, "semantic-compatibility-section-invalid", f"{section} must be a non-empty object")
                continue
            for key, version in contracts.items():
                if not isinstance(key, str) or not key:
                    self._error(path, "semantic-compatibility-contract-invalid", f"{section} contains an empty contract key")
                if not isinstance(version, str) or not SEMVER_RE.match(version):
                    self._error(path, "semantic-compatibility-contract-version-invalid", f"{section}.{key} must use semver: {version!r}")

        deprecated = document.get("deprecated_contracts")
        if not isinstance(deprecated, list) or not all(isinstance(item, str) and item for item in deprecated):
            self._error(path, "semantic-compatibility-deprecated-invalid", "deprecated_contracts must be a list of strings")

        registered_agent_types = self._registered_agent_types()
        matrix_agent_types = set(document.get("agent_contracts", {})) if isinstance(document.get("agent_contracts"), dict) else set()
        missing_agents = sorted(registered_agent_types - matrix_agent_types)
        extra_agents = sorted(matrix_agent_types - registered_agent_types)
        if missing_agents:
            self._warning(path, "semantic-compatibility-agent-missing", f"Registered agents missing from compatibility matrix: {', '.join(missing_agents)}")
        if extra_agents:
            self._warning(path, "semantic-compatibility-agent-extra", f"Compatibility matrix agents not present in registry manifest: {', '.join(extra_agents)}")

    def _validate_model_registry_runtime_alignment(self) -> None:
        """Validate Layer 4 model runtime selectors and environment stage policy."""
        runtime_models = self._runtime_model_references()
        if not runtime_models:
            self._error(MODEL_REGISTRY_SERVICE_PATH, "runtime-models-missing", "No runtime model selectors found for Layer 4")
            return

        registered_models = self._registered_registry_models()
        missing_models = sorted(runtime_models - registered_models)
        if missing_models:
            self._error(
                self.registry_root / "README.md",
                "runtime-model-unregistered",
                f"Runtime model selectors missing from contracts/agent-registry README model inventory: {', '.join(missing_models)}",
            )

        service_text = MODEL_REGISTRY_SERVICE_PATH.read_text(encoding="utf-8") if MODEL_REGISTRY_SERVICE_PATH.exists() else ""
        if "allowed_transitions" not in service_text:
            self._error(MODEL_REGISTRY_SERVICE_PATH, "stage-policy-missing", "Model registry service must declare explicit allowed stage transitions")
        for stage in sorted(ALLOWED_MODEL_STAGES):
            if f"\"{stage}\"" not in service_text and f"'{stage}'" not in service_text:
                self._error(MODEL_REGISTRY_SERVICE_PATH, "stage-policy-missing-value", f"Model registry service missing stage policy value: {stage}")

        routes_text = MODEL_REGISTRY_ROUTES_PATH.read_text(encoding="utf-8") if MODEL_REGISTRY_ROUTES_PATH.exists() else ""
        if "AuditAction.MODEL_EVALUATED" not in routes_text:
            self._error(MODEL_REGISTRY_ROUTES_PATH, "audit-eval-missing", "Eval score updates must emit AuditAction.MODEL_EVALUATED")
        if "AuditAction.MODEL_PROMOTED" not in service_text or "AuditAction.MODEL_DEPRECATED" not in service_text:
            self._error(MODEL_REGISTRY_SERVICE_PATH, "audit-promotion-missing", "Model stage transitions must emit MODEL_PROMOTED/MODEL_DEPRECATED audit events")

    def _registered_registry_models(self) -> set[str]:
        readme_path = self.registry_root / "README.md"
        if not readme_path.exists():
            self._error(readme_path, "registry-readme-missing", "contracts/agent-registry/README.md is required for runtime-model alignment checks")
            return set()
        text = readme_path.read_text(encoding="utf-8")
        return set(re.findall(r"`([a-zA-Z0-9_.:-]+)`", text))

    def _runtime_model_references(self) -> set[str]:
        model_names: set[str] = set()
        for path in (MODEL_REGISTRY_SERVICE_PATH, L4_SETTINGS_PATH):
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            model_names.update(re.findall(r"(gpt-[a-zA-Z0-9_.-]+|claude-[a-zA-Z0-9_.-]+)", text))
        return model_names

    def _registered_agent_types(self) -> set[str]:
        path = self.registry_root / "agents" / "manifest.json"
        document = self.documents.get(path)
        if not isinstance(document, dict) or not isinstance(document.get("agents"), list):
            return set()
        return {
            agent["agent_type"]
            for agent in document["agents"]
            if isinstance(agent, dict) and isinstance(agent.get("agent_type"), str) and agent.get("agent_type")
        }

    def _validate_relative_file_reference(self, path: Path, document: dict[str, Any], field: str) -> None:
        reference = document.get(field)
        if not isinstance(reference, str) or not reference:
            self._error(path, "file-reference-missing", f"Document is missing {field}")
        elif not (path.parent / reference).resolve().exists():
            self._error(path, "file-reference-invalid", f"{field} does not exist: {reference}")

    def _canonical_agent_types(self) -> set[str]:
        if not AGENT_TAXONOMY_PATH.exists():
            self._warning(AGENT_TAXONOMY_PATH, "agent-taxonomy-missing", "Agent taxonomy source file is missing")
            return set()

        text = AGENT_TAXONOMY_PATH.read_text(encoding="utf-8")
        active_section = text.split("# ── Deprecated aliases", 1)[0]
        try:
            tree = ast.parse(active_section)
        except SyntaxError as exc:
            self._warning(AGENT_TAXONOMY_PATH, "agent-taxonomy-unparseable", f"Could not parse active agent taxonomy: {exc}")
            return set()

        values: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or node.name != "AgentType":
                continue
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    if stmt.value.value.endswith("Agent") or stmt.value.value.endswith("Controller"):
                        values.add(stmt.value.value)
        return values

    def _canonical_workflow_types(self) -> set[str]:
        if not WORKFLOW_CONFIG_PATH.exists():
            self._warning(WORKFLOW_CONFIG_PATH, "workflow-config-missing", "Workflow config source file is missing")
            return set()

        text = WORKFLOW_CONFIG_PATH.read_text(encoding="utf-8")
        return set(re.findall(r"workflow_type\s*=\s*[\"']([^\"']+)[\"']", text))

    def _error(self, path: Path, rule: str, message: str) -> None:
        self.errors.append(Finding("ERROR", path, rule, message))

    def _warning(self, path: Path, rule: str, message: str) -> None:
        self.warnings.append(Finding("WARN", path, rule, message))

    def _report(self) -> int:
        print("Agent Registry Validation")
        print("=" * 60)
        print(f"Registry root: {self.registry_root.relative_to(REPO_ROOT) if self.registry_root.is_relative_to(REPO_ROOT) else self.registry_root}")
        print(f"Mode: {'strict' if self.strict else 'warning'}")
        print(f"JSON documents parsed: {len(self.documents)}")
        print()

        for severity, findings in (("ERROR", self.errors), ("WARN", self.warnings)):
            if not findings:
                print(f"{severity}: 0")
                continue
            print(f"{severity}: {len(findings)}")
            by_rule: dict[str, list[Finding]] = {}
            for finding in findings:
                by_rule.setdefault(finding.rule, []).append(finding)
            for rule, rule_findings in sorted(by_rule.items()):
                print(f"  {rule}: {len(rule_findings)}")
                for finding in rule_findings[:5]:
                    display_path = finding.path.relative_to(REPO_ROOT) if finding.path.is_absolute() and finding.path.is_relative_to(REPO_ROOT) else finding.path
                    print(f"    {display_path} - {finding.message}")
                if len(rule_findings) > 5:
                    print(f"    ... and {len(rule_findings) - 5} more")
            print()

        if self.errors:
            print("Result: failed because registry contract errors were found.")
            return 1
        if self.strict and self.warnings:
            print("Result: failed because AGENT_REGISTRY_STRICT is enabled and warnings were found.")
            return 1
        if self.warnings:
            print("Result: passed in warning mode; resolve warnings before enabling runtime enforcement.")
            return 0
        print("Result: passed; no registry contract findings.")
        return 0


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Layer 4 agent-registry contracts")
    parser.add_argument(
        "registry_root",
        nargs="?",
        default=str(DEFAULT_REGISTRY_ROOT),
        help="Path to contracts/agent-registry (default: contracts/agent-registry)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat semantic coverage warnings as blocking failures",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    strict = args.strict or os.getenv("AGENT_REGISTRY_STRICT") == "1"
    registry_root = Path(args.registry_root)
    if not registry_root.is_absolute():
        registry_root = REPO_ROOT / registry_root
    return RegistryValidator(registry_root.resolve(), strict).validate()


if __name__ == "__main__":
    sys.exit(main())
