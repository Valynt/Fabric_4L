"""Local adapter boundary for controlled ``value_fabric`` imports.

Service code should import shared/runtime symbols via this module to avoid
accidental deep imports from non-public ``value_fabric`` paths.
"""

from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.error_handling.exceptions import ValueFabricException
from value_fabric.shared.identity.context import RequestContext, get_request_context
from value_fabric.shared.identity.fabric_auth import register_fabric_auth_from_env
from value_fabric.shared.identity.middleware import GovernanceMiddleware
from value_fabric.shared.identity.rate_limiter import RedisRateLimiter
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.startup import reject_insecure_bypass_in_production


def map_exception_to_contract_detail(
    exc: ValueFabricException,
    *,
    request_id: str | None = None,
) -> dict[str, object | None]:
    """Map shared exception primitives to the Layer 3 flat contract shape."""
    return {
        "error": str(exc.error_code),
        "message": exc.message,
        "details": exc.details,
        "request_id": request_id,
    }
