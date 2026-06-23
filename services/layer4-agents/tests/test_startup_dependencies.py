from __future__ import annotations

import pytest

from layer4_agents.startup_dependencies import verify_startup_dependencies


def test_dependency_gate_fail_closed_in_production_for_missing_required_module(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    with pytest.raises(RuntimeError, match="weasyprint"):
        verify_startup_dependencies(environment="production")


def test_dependency_gate_permissive_in_development_for_missing_required_module(monkeypatch):
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    verify_startup_dependencies(environment="development")
