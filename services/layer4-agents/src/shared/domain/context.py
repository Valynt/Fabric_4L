"""Compatibility shim for the canonical Layer 4 tenant context module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_canonical_module() -> ModuleType:
    canonical_path = (
        Path(__file__).resolve().parents[2]
        / "layer4_agents"
        / "shared"
        / "domain"
        / "context.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_layer4_agents_canonical_shared_domain_context",
        canonical_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load canonical tenant context module: {canonical_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_canonical = _load_canonical_module()
for _name, _value in vars(_canonical).items():
    if not _name.startswith("_"):
        globals()[_name] = _value

__all__ = [_name for _name in globals() if not _name.startswith("_")]
