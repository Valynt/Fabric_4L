"""Shared framework imports for the Layer 5 service.

This module intentionally uses normal package imports only; Docker images and
local test commands must provide repository/package roots on PYTHONPATH.
"""

from collections.abc import Callable
from typing import Any, cast

from value_fabric.shared.fastapi_framework.app import (
    create_fabric_app,
    install_metrics_middleware,
)
from value_fabric.shared.fastapi_framework.middleware import resolve_cors_policy
from value_fabric.shared.observability.metrics_access import verify_metrics_access
from value_fabric.shared.security.config import validate_production_safety
from value_fabric.shared.security.middleware import (
    SecurityConfig,
    add_security_middleware,
)

create_fabric_app = cast(Callable[..., Any], create_fabric_app)
install_metrics_middleware = cast(Callable[..., Any], install_metrics_middleware)
resolve_cors_policy = cast(Callable[..., Any], resolve_cors_policy)
verify_metrics_access = cast(Callable[..., bool], verify_metrics_access)
validate_production_safety = cast(Callable[..., None], validate_production_safety)
SecurityConfig = cast(Any, SecurityConfig)
add_security_middleware = cast(Callable[..., None], add_security_middleware)

