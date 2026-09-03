from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "check_agent_registry",
    ROOT / "scripts" / "ci" / "check_agent_registry.py",
)
check_agent_registry = importlib.util.module_from_spec(SPEC)
sys.modules["check_agent_registry"] = check_agent_registry
assert SPEC and SPEC.loader
SPEC.loader.exec_module(check_agent_registry)


def make_tool(name: str, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "name": name,
        "manifest_path": f"{name}.json",
        "tenant_required": True,
        "tenant_scope": "TENANT",
        "provenance": {
            "required": True,
            "fields": ["tenant_id", "trace_id", "tool_name", "tool_version", "caller_agent_type"],
        },
    }
    data.update(overrides)
    return data


class AgentRegistryValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.registry = self.root / "agent-registry"
        (self.registry / "tools").mkdir(parents=True)
        (self.registry / "prompts").mkdir()
        (self.registry / "skills").mkdir()
        # Each validator is constructed with a fake repo root via patched module
        # constants below; the registry_root is a temp directory we fully control.

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_tool_manifest(self, tools: list[dict[str, object]]) -> None:
        (self.registry / "tools" / "manifest.json").write_text(
            json.dumps({"tools": tools}, indent=2) + "\n",
            encoding="utf-8",
        )
        # Stub out referenced tool manifest files so path resolution passes.
        for tool in tools:
            manifest_path = str(tool.get("manifest_path", ""))
            if manifest_path:
                (self.registry / "tools" / manifest_path).write_text(
                    "{}\n", encoding="utf-8"
                )

    def build_validator(self, strict: bool = False) -> check_agent_registry.RegistryValidator:
        return check_agent_registry.RegistryValidator(self.registry, strict)

    def test_tool_manifest_missing_tenant_scope_is_error(self) -> None:
        self.write_tool_manifest([make_tool("alpha", tenant_scope=None)])
        validator = self.build_validator()
        validator._load_json_documents()
        validator._validate_tool_manifest()
        self.assertTrue(
            any(f.rule == "tool-tenant-scope-invalid" for f in validator.errors),
            [f.message for f in validator.errors],
        )

    def test_tool_manifest_invalid_tenant_scope_is_error(self) -> None:
        self.write_tool_manifest([make_tool("alpha", tenant_scope="ALL")])
        validator = self.build_validator()
        validator._load_json_documents()
        validator._validate_tool_manifest()
        self.assertTrue(
            any(f.rule == "tool-tenant-scope-invalid" for f in validator.errors),
            [f.message for f in validator.errors],
        )

    def test_tool_manifest_valid_tenant_scope_passes(self) -> None:
        self.write_tool_manifest([make_tool("alpha")])
        validator = self.build_validator()
        validator._load_json_documents()
        validator._validate_tool_manifest()
        self.assertEqual(validator.errors, [])

    def test_tool_manifest_global_scope_is_accepted(self) -> None:
        self.write_tool_manifest([make_tool("alpha", tenant_scope="GLOBAL")])
        validator = self.build_validator()
        validator._load_json_documents()
        validator._validate_tool_manifest()
        self.assertEqual(validator.errors, [])

    def test_tool_manifest_missing_tenant_required_is_error(self) -> None:
        self.write_tool_manifest([make_tool("alpha", tenant_required=False)])
        validator = self.build_validator()
        validator._load_json_documents()
        validator._validate_tool_manifest()
        self.assertTrue(
            any(f.rule == "tool-tenant-required" for f in validator.errors),
            [f.message for f in validator.errors],
        )

    def test_prompt_runtime_drift_emits_warning(self) -> None:
        # A runtime prompt file that has no registry entry -> warning.
        runtime = self.root / "services" / "layer4-agents" / "prompts" / "workflow" / "v1"
        runtime.mkdir(parents=True)
        (runtime / "orphan.md").write_text("# orphan", encoding="utf-8")

        validator = self.build_validator(strict=False)
        with patch.object(check_agent_registry, "PROMPTS_RUNTIME_ROOT", runtime):
            validator._validate_prompt_runtime_drift()
        self.assertTrue(
            any(f.rule == "prompt-runtime-unregistered" for f in validator.warnings),
            [f.message for f in validator.warnings],
        )

    def test_prompt_runtime_drift_blocks_in_strict_mode(self) -> None:
        runtime = self.root / "services" / "layer4-agents" / "prompts" / "workflow" / "v1"
        runtime.mkdir(parents=True)
        (runtime / "orphan.md").write_text("# orphan", encoding="utf-8")

        validator = self.build_validator(strict=True)
        with patch.object(check_agent_registry, "PROMPTS_RUNTIME_ROOT", runtime):
            validator._validate_prompt_runtime_drift()
        self.assertTrue(
            any(f.rule == "prompt-runtime-unregistered" for f in validator.warnings),
            [f.message for f in validator.warnings],
        )

    def test_skill_runtime_drift_emits_warning(self) -> None:
        skills = self.root / "services" / "layer4-agents" / "skills"
        skills.mkdir(parents=True)
        (skills / "orphan.md").write_text("# orphan", encoding="utf-8")

        validator = self.build_validator(strict=False)
        with patch.object(check_agent_registry, "SKILLS_RUNTIME_ROOT", skills):
            validator._validate_skill_runtime_drift()
        self.assertTrue(
            any(f.rule == "skill-runtime-unregistered" for f in validator.warnings),
            [f.message for f in validator.warnings],
        )

    def test_report_returns_failure_for_errors(self) -> None:
        validator = self.build_validator(strict=False)
        validator._error(self.registry, "test-rule", "boom")
        self.assertEqual(validator._report(), 1)

    def test_report_returns_failure_for_warnings_in_strict(self) -> None:
        validator = self.build_validator(strict=True)
        validator._warning(self.registry, "test-rule", "warn")
        self.assertEqual(validator._report(), 1)

    def test_report_returns_zero_for_warnings_in_warning_mode(self) -> None:
        validator = self.build_validator(strict=False)
        validator._warning(self.registry, "test-rule", "warn")
        self.assertEqual(validator._report(), 0)

    def test_required_layout_includes_skill_schema(self) -> None:
        validator = self.build_validator()
        validator._validate_required_layout()
        self.assertTrue(
            any(f.rule == "required-file-missing" and "schemas/skill.schema.json" in f.message for f in validator.errors),
            [f.message for f in validator.errors],
        )

    def test_main_runs_clean_against_production_registry(self) -> None:
        # The committed registry is clean even in strict mode (CI gate).
        self.assertEqual(check_agent_registry.main([str(ROOT / "contracts" / "agent-registry"), "--strict"]), 0)


if __name__ == "__main__":
    unittest.main()
