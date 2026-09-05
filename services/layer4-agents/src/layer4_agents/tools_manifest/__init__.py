"""Tool Manifest Registry — load, validate, and filter tool manifests.

This package consumes YAML tool manifests from the canonical
:file:`contracts/tool-manifests/` tree and produces the compiled index
used by Layer 4 at runtime.
"""

from .loader import filter_tools_for_agent, load_manifests
from .models import ToolManifest, ToolRegistryIndex

__all__ = ["filter_tools_for_agent", "load_manifests", "ToolManifest", "ToolRegistryIndex"]
