from __future__ import annotations

import pytest

import layer4_agents.tools as tools
from layer4_agents.tools import registry as registry_module


def test_default_registry_populates_all_supported_tool_categories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for layer in (1, 2, 3, 5):
        monkeypatch.setenv(f"LAYER{layer}_API_URL", f"https://layer{layer}.test")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")
    monkeypatch.setattr(registry_module, "_global_registry", None)

    registry = tools.create_default_registry(config={"request_timeout": 1})

    names = {metadata.name for metadata in registry.list_tools()}
    assert len(names) == 26
    assert {"query_graph", "calculate_roi", "generate_section", "analyze_competition"} <= names
    assert tools.create_default_registry() is registry


def test_tool_package_lazy_exports_and_rejects_unknown_names() -> None:
    assert tools.__getattr__("ValidateInputTool").__name__ == "ValidateInputTool"
    assert tools.__getattr__("create_signal").__name__ == "create_signal"
    with pytest.raises(AttributeError, match="unknown_tool"):
        tools.__getattr__("unknown_tool")
