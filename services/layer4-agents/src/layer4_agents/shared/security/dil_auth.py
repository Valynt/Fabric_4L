from __future__ import annotations

"""Re-export from top-level shared.security.dil_auth.

This module exists because layer4-agents/src/shared/ shadows the top-level
packages/shared/src/value_fabric/shared/ package when 'src' is on sys.path.
"""

import importlib.util
from pathlib import Path

# Resolve the real dil_auth module from the top-level shared package
_top_level_shared = Path(__file__).resolve().parent.parent.parent.parent.parent / "shared" / "security" / "dil_auth.py"

if _top_level_shared.exists():
    spec = importlib.util.spec_from_file_location(
        "shared.security._dil_auth_real",
        str(_top_level_shared),
    )
    _real_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_real_mod)

    # Re-export everything
    for _name in dir(_real_mod):
        if not _name.startswith("_"):
            globals()[_name] = getattr(_real_mod, _name)
    # Also export private names needed by tests
    for _name in ["_is_blocked_ip", "_is_encoded_ip", "_BLOCKED_NETWORKS"]:
        if hasattr(_real_mod, _name):
            globals()[_name] = getattr(_real_mod, _name)
else:
    raise ImportError(f"Cannot find top-level dil_auth.py at {_top_level_shared}")
