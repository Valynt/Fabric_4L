"""Unit tests for the Layer 4 PromptRegistry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from layer4_agents.harness.prompt_registry import PromptRegistry


@pytest.fixture
def prompts_dir(tmp_path: Path) -> Path:
    """Return a temporary prompts tree with one workflow/version/prompt."""
    root = tmp_path / "prompts"
    workflow_dir = root / "test_workflow" / "v1"
    workflow_dir.mkdir(parents=True)
    body = "Say hello to {{ name }}."
    frontmatter = (
        "---\n"
        "prompt_id: test.hello\n"
        "version: v1\n"
        "workflow_type: test_workflow\n"
        "model_task: reasoning\n"
        "temperature: 0.5\n"
        "max_tokens: 100\n"
        "---\n\n"
    )
    (workflow_dir / "hello.md").write_text(frontmatter + body, encoding="utf-8")
    return root


@pytest.fixture
def baselines_dir(tmp_path: Path) -> Path:
    root = tmp_path / "baselines"
    root.mkdir()
    return root


def test_prompt_registry_computes_content_hash(prompts_dir: Path) -> None:
    registry = PromptRegistry(prompts_root=prompts_dir)
    template = registry.get("test_workflow", "hello")

    expected = hashlib.sha256("Say hello to {{ name }}.".encode("utf-8")).hexdigest()
    assert template.content_hash == expected


def test_prompt_registry_to_prompt_ref_includes_hash(prompts_dir: Path) -> None:
    registry = PromptRegistry(prompts_root=prompts_dir)
    template = registry.get("test_workflow", "hello")

    ref = template.to_prompt_ref(reasoning_policy_id="default_copilot")
    assert ref["prompt_id"] == "test.hello"
    assert ref["version"] == "v1"
    assert ref["reasoning_policy_id"] == "default_copilot"
    assert ref["content_hash"] == template.content_hash


def test_prompt_registry_baseline_for_returns_none_when_missing(
    prompts_dir: Path, baselines_dir: Path
) -> None:
    registry = PromptRegistry(prompts_root=prompts_dir, baselines_root=baselines_dir)
    assert registry.baseline_for("test.hello", "v1") is None


def test_prompt_registry_baseline_for_loads_existing_baseline(
    prompts_dir: Path, baselines_dir: Path
) -> None:
    baseline = {
        "prompt_id": "test.hello",
        "version": "v1",
        "content_hash": "abcd" * 16,
        "score": 0.85,
        "eval_set_id": "unit-test",
        "recorded_at": "2026-09-01T00:00:00Z",
    }
    baseline_path = baselines_dir / "prompt-test.hello-v1.json"
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")

    registry = PromptRegistry(prompts_root=prompts_dir, baselines_root=baselines_dir)
    loaded = registry.baseline_for("test.hello", "v1")
    assert loaded == baseline


def test_prompt_registry_preload_loads_all_prompts(prompts_dir: Path) -> None:
    registry = PromptRegistry(prompts_root=prompts_dir)
    count = registry.preload("test_workflow")
    assert count == 1
    assert registry.list_prompts() == ["test_workflow/v1/hello"]


def test_get_missing_prompt_raises_file_not_found(prompts_dir: Path) -> None:
    registry = PromptRegistry(prompts_root=prompts_dir)
    with pytest.raises(FileNotFoundError):
        registry.get("test_workflow", "does_not_exist")


def test_get_malformed_frontmatter_raises_value_error(tmp_path: Path) -> None:
    root = tmp_path / "prompts"
    workflow_dir = root / "bad_workflow" / "v1"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "no_frontmatter.md").write_text(
        "This file has no YAML frontmatter at all.", encoding="utf-8"
    )

    registry = PromptRegistry(prompts_root=root)
    with pytest.raises(ValueError):
        registry.get("bad_workflow", "no_frontmatter")


def test_preload_skips_prompts_with_errors(tmp_path: Path) -> None:
    root = tmp_path / "prompts"
    workflow_dir = root / "mixed_workflow" / "v1"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "valid.md").write_text(
        "---\nprompt_id: mixed.valid\nversion: v1\n---\n\nValid body.",
        encoding="utf-8",
    )
    (workflow_dir / "broken.md").write_text("No frontmatter here.", encoding="utf-8")

    registry = PromptRegistry(prompts_root=root)
    count = registry.preload("mixed_workflow")
    assert count == 1
    assert registry.list_prompts() == ["mixed_workflow/v1/valid"]
