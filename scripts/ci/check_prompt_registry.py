#!/usr/bin/env python3
"""CI gate: prompt-version registry + agent operating contracts.

Closes the drift gap between prompt files, agent definitions, and eval
infrastructure by enforcing, from a single machine-readable source of truth
under ``contracts/agent-registry``:

1. Every prompt contract declares a ``content_hash`` matching the SHA-256 of
   the referenced prompt file body, so undeclared prompt-content drift fails.
2. A prompt version bump is accompanied by a changelog entry.
3. Declared eval baseline artifacts exist and agree with the contract.
4. Every agent operating contract is present, valid, and cross-checked against
   the tool registry and the agent manifest.

The gate follows the repo's "warning then enforce" rollout policy: malformed
registry documents and broken file references are always blocking; semantic
cross-checks are warnings by default and become blocking when
``PROMPT_REGISTRY_STRICT=1`` is set or ``--strict`` is passed.

Full JSON-Schema validation is owned by ``tests/contract`` (pytest), which
runs in the same ``gate-api-contracts`` gate; this script intentionally stays
dependency-free and structural, mirroring ``check_agent_registry.py``.

Usage:
    python scripts/ci/check_prompt_registry.py
    python scripts/ci/check_prompt_registry.py --strict
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_ROOT = REPO_ROOT / "contracts" / "agent-registry"

SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

PROMPT_REQUIRED_FIELDS = (
    "id",
    "version",
    "kind",
    "prompt_path",
    "inputs",
    "outputs",
    "reasoning_policy",
    "changelog",
)

AGENT_CONTRACT_REQUIRED_FIELDS = (
    "agent_type",
    "tools",
    "memory_scopes",
    "permissions",
    "eval_target",
)


@dataclass(frozen=True)
class Finding:
    """A prompt-registry validation finding."""

    severity: str
    path: Path
    rule: str
    message: str


class PromptRegistryGate:
    """Validates prompt-version contracts and agent operating contracts."""

    def __init__(self, registry_root: Path, strict: bool) -> None:
        self.registry_root = registry_root
        self.strict = strict
        self.errors: list[Finding] = []
        self.warnings: list[Finding] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _error(self, path: Path, rule: str, message: str) -> None:
        self.errors.append(Finding("ERROR", path, rule, message))

    def _warn(self, path: Path, rule: str, message: str) -> None:
        self.warnings.append(Finding("WARN", path, rule, message))

    def _load_json(self, path: Path) -> dict[str, Any] | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            self._error(
                path,
                "invalid-json",
                f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            )
            return None
        except OSError as exc:
            self._error(path, "unreadable", f"Could not read file: {exc}")
            return None

    def _resolve_within_repo(self, rel_path: str, base: Path, contract_path: Path) -> Path | None:
        """Resolve a repo-relative reference, rejecting paths that escape REPO_ROOT."""
        resolved = (base.parent / rel_path).resolve()
        if not resolved.is_relative_to(REPO_ROOT):
            self._error(
                contract_path,
                "path-escape",
                f"Path escapes the repository root: {rel_path!r} resolves to {resolved}",
            )
            return None
        return resolved

    @staticmethod
    def _sha256_hex(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    # ------------------------------------------------------------------
    # Validation entrypoint
    # ------------------------------------------------------------------

    def validate(self) -> int:
        if not self.registry_root.exists():
            self._error(
                self.registry_root,
                "registry-missing",
                "Agent registry directory does not exist",
            )
            return self._report()

        tool_names = self._load_tool_names()
        manifest_agents = self._load_agent_manifest()
        self._validate_prompts()
        self._validate_agent_contracts(manifest_agents, tool_names)
        return self._report()

    # ------------------------------------------------------------------
    # Tool registry
    # ------------------------------------------------------------------

    def _load_tool_names(self) -> set[str]:
        tool_manifest = self.registry_root / "tools" / "manifest.json"
        document = self._load_json(tool_manifest)
        if document is None:
            return set()
        tools = document.get("tools", [])
        if not isinstance(tools, list):
            self._error(tool_manifest, "tool-manifest-invalid", "tools/manifest.json 'tools' must be a list")
            return set()
        return {tool.get("name") for tool in tools if isinstance(tool, dict) and tool.get("name")}

    # ------------------------------------------------------------------
    # Agent manifest
    # ------------------------------------------------------------------

    def _load_agent_manifest(self) -> dict[str, Any] | None:
        manifest_path = self.registry_root / "agents" / "manifest.json"
        document = self._load_json(manifest_path)
        if document is None:
            return None
        agents = document.get("agents")
        if not isinstance(agents, list):
            self._error(manifest_path, "agent-manifest-invalid", "agents/manifest.json 'agents' must be a list")
            return None
        return document

    # ------------------------------------------------------------------
    # Prompt contracts
    # ------------------------------------------------------------------

    def _validate_prompts(self) -> None:
        prompts_dir = self.registry_root / "prompts"
        if not prompts_dir.exists():
            self._error(prompts_dir, "prompts-dir-missing", "prompts/ directory does not exist")
            return

        contract_paths = sorted(prompts_dir.glob("*.json"))
        if not contract_paths:
            self._warn(prompts_dir, "no-prompt-contracts", "No prompt contract JSONs found in prompts/")

        for path in contract_paths:
            self._validate_prompt_contract(path)

    def _validate_prompt_contract(self, path: Path) -> None:
        contract = self._load_json(path)
        if contract is None:
            return

        if contract.get("kind") != "prompt":
            self._error(path, "prompt-kind-invalid", "Prompt registry entries must use kind=prompt")
            return

        for field in PROMPT_REQUIRED_FIELDS:
            if field not in contract:
                self._error(path, "prompt-field-missing", f"Prompt registry entry missing {field}")

        version = contract.get("version")
        if not isinstance(version, str) or not SEMVER_RE.match(version):
            self._error(path, "prompt-version-invalid", "Prompt version must be semver (x.y.z)")

        # Resolve and hash the referenced prompt file.
        prompt_path = contract.get("prompt_path")
        if not isinstance(prompt_path, str):
            return
        prompt_file = self._resolve_within_repo(prompt_path, path, path)
        if prompt_file is None:
            return
        if not prompt_file.exists():
            self._error(path, "prompt-file-missing", f"Prompt file does not exist: {prompt_file}")
            return

        declared_hash = contract.get("content_hash")
        if not declared_hash:
            self._warn(
                path,
                "prompt-hash-missing",
                "Prompt contract does not declare content_hash; drift protection not yet enabled",
            )
        elif not isinstance(declared_hash, str) or not SHA256_RE.match(declared_hash):
            self._error(path, "prompt-hash-malformed", "content_hash must be a 64-char hex SHA-256 digest")
        else:
            computed_hash = self._sha256_hex(prompt_file)
            if computed_hash != declared_hash:
                self._error(
                    path,
                    "prompt-content-drift",
                    f"Content hash mismatch: declared {declared_hash}, computed {computed_hash}. "
                    "Bump the prompt version and update the changelog if this change is intentional.",
                )

        self._validate_prompt_changelog(path, contract, version)
        self._validate_prompt_baseline(path, contract)

    def _validate_prompt_changelog(self, path: Path, contract: dict[str, Any], version: str | None) -> None:
        changelog = contract.get("changelog")
        if not isinstance(changelog, list) or not changelog:
            self._error(path, "prompt-changelog-missing", "Prompt contract must include a non-empty changelog")
            return
        if version and not any(entry.get("version") == version for entry in changelog if isinstance(entry, dict)):
            self._warn(
                path,
                "prompt-version-unreported",
                f"Changelog has no entry for current version {version}",
            )

    def _validate_prompt_baseline(self, path: Path, contract: dict[str, Any]) -> None:
        baseline = contract.get("eval_baseline")
        if baseline is None:
            self._warn(path, "prompt-baseline-missing", "Prompt contract does not declare eval_baseline")
            return

        rel_path = baseline.get("baseline_file") if isinstance(baseline, dict) else None
        if not rel_path:
            self._warn(path, "prompt-baseline-unreferenced", "eval_baseline missing baseline_file")
            return

        baseline_file = self._resolve_within_repo(rel_path, path, path)
        if baseline_file is None:
            return
        if not baseline_file.exists():
            self._error(path, "prompt-baseline-file-missing", f"Eval baseline file does not exist: {baseline_file}")
            return

        artifact = self._load_json(baseline_file)
        if artifact is None:
            return

        required = {"prompt_id", "version", "content_hash", "score", "eval_set_id", "recorded_at"}
        missing = required - set(artifact)
        if missing:
            self._error(
                baseline_file,
                "baseline-fields-missing",
                f"Eval baseline missing required fields: {sorted(missing)}",
            )

        if artifact.get("prompt_id") != contract.get("id"):
            self._error(baseline_file, "baseline-prompt-id-mismatch", "Baseline prompt_id does not match contract id")
        if artifact.get("version") != contract.get("version"):
            self._error(baseline_file, "baseline-version-mismatch", "Baseline version does not match contract version")
        if artifact.get("content_hash") != contract.get("content_hash"):
            self._warn(
                baseline_file,
                "baseline-hash-stale",
                "Baseline content_hash does not match the contract content_hash",
            )

    # ------------------------------------------------------------------
    # Agent operating contracts
    # ------------------------------------------------------------------

    def _validate_agent_contracts(self, manifest: dict[str, Any] | None, tool_names: set[str]) -> None:
        agents_dir = self.registry_root / "agents"
        contract_paths = sorted(agents_dir.glob("*.contract.json"))
        if not contract_paths:
            self._warn(agents_dir, "no-agent-contracts", "No agent operating contracts found in agents/")
            return

        if manifest is None:
            return

        manifest_agents = {
            entry.get("agent_type"): entry
            for entry in manifest.get("agents", [])
            if isinstance(entry, dict) and entry.get("agent_type")
        }
        if not manifest_agents:
            self._error(agents_dir, "agent-manifest-empty", "agents/manifest.json declares no agents")
            return

        for path in contract_paths:
            self._validate_agent_contract(path, manifest_agents, tool_names)

    def _validate_agent_contract(
        self,
        path: Path,
        manifest_agents: dict[str, dict[str, Any]],
        tool_names: set[str],
    ) -> None:
        contract = self._load_json(path)
        if contract is None:
            return

        if contract.get("kind") != "agent_contract":
            self._error(path, "agent-contract-kind-invalid", "Agent operating contracts must use kind=agent_contract")
            return

        for field in AGENT_CONTRACT_REQUIRED_FIELDS:
            if field not in contract:
                self._error(path, "agent-contract-field-missing", f"Agent operating contract missing {field}")

        agent_type = contract.get("agent_type")
        if not agent_type:
            self._error(path, "agent-contract-agent-type-missing", "Agent operating contract missing agent_type")
            return

        if agent_type not in manifest_agents:
            self._warn(path, "agent-contract-unmanifested", f"agent_type {agent_type} is not listed in agents/manifest.json")
        else:
            manifest_entry = manifest_agents[agent_type]
            declared_path = manifest_entry.get("operating_contract_path")
            if declared_path and Path(declared_path).name != path.name:
                self._warn(
                    path,
                    "agent-contract-manifest-path-mismatch",
                    f"manifest operating_contract_path {declared_path} does not match {path.name}",
                )

        tools = contract.get("tools")
        if isinstance(tools, list):
            for tool in tools:
                if tool not in tool_names:
                    self._warn(
                        path,
                        "agent-contract-unknown-tool",
                        f"Tool {tool!r} is not registered in tools/manifest.json",
                    )
        else:
            self._error(path, "agent-contract-tools-invalid", "Agent operating contract 'tools' must be a list")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def _report(self) -> int:
        print("Prompt Registry Validation")
        print("=" * 60)
        print(f"Registry root: {self.registry_root.relative_to(REPO_ROOT) if self.registry_root.is_relative_to(REPO_ROOT) else self.registry_root}")
        print(f"Mode: {'strict' if self.strict else 'warning'}")
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
                    display_path = (
                        finding.path.relative_to(REPO_ROOT)
                        if finding.path.is_absolute() and finding.path.is_relative_to(REPO_ROOT)
                        else finding.path
                    )
                    print(f"    {display_path} - {finding.message}")
                if len(rule_findings) > 5:
                    print(f"    ... and {len(rule_findings) - 5} more")
            print()

        if self.errors:
            print("Result: failed because prompt/agent contract errors were found.")
            return 1
        if self.strict and self.warnings:
            print("Result: failed because PROMPT_REGISTRY_STRICT is enabled and warnings were found.")
            return 1
        if self.warnings:
            print("Result: passed in warning mode; resolve warnings before enabling enforcement.")
            return 0
        print("Result: passed; no prompt-registry findings.")
        return 0


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate prompt-version registry and agent operating contracts")
    parser.add_argument(
        "registry_root",
        nargs="?",
        default=str(DEFAULT_REGISTRY_ROOT),
        help="Path to contracts/agent-registry (default: contracts/agent-registry)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat semantic cross-check warnings as blocking failures",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    strict = args.strict or os.getenv("PROMPT_REGISTRY_STRICT") == "1"
    registry_root = Path(args.registry_root)
    if not registry_root.is_absolute():
        registry_root = REPO_ROOT / registry_root
    return PromptRegistryGate(registry_root.resolve(), strict).validate()


if __name__ == "__main__":
    sys.exit(main())
