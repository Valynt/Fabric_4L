from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, cast

def _resolve_shared_src() -> Path | None:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "packages" / "shared" / "src"
        if candidate.exists():
            return candidate
    return None


_SHARED_SRC = _resolve_shared_src()
if _SHARED_SRC and str(_SHARED_SRC) not in sys.path:
    sys.path.insert(0, str(_SHARED_SRC))

_framework_app = import_module("value_fabric.shared.fastapi_framework.app")
_security_config = import_module("value_fabric.shared.security.config")

create_fabric_app = cast(Callable[..., Any], _framework_app.create_fabric_app)
register_health_endpoint = cast(Callable[..., None], _framework_app.register_health_endpoint)
validate_production_safety = cast(Callable[..., None], _security_config.validate_production_safety)

EnforcementControlConfig = _framework_app.EnforcementControlConfig
EnforcementMode = _framework_app.EnforcementMode
EnforcementRolloutConfig = _framework_app.EnforcementRolloutConfig
