"""Local adapter boundary for controlled ``value_fabric`` imports.

Service code should import shared/runtime symbols via this module to avoid
accidental deep imports from non-public ``value_fabric`` paths.
"""

from value_fabric.public_api import shared
from value_fabric.shared.error_handling.exceptions import ValueFabricException

# Re-export stable shared API entrypoints used by service runtime modules.
TypedDictModel = shared.TypedDictModel
RequestContext = shared.RequestContext
get_request_context = shared.get_request_context
GovernanceMiddleware = shared.GovernanceMiddleware
register_exception_handlers = shared.register_exception_handlers
RedisRateLimiter = shared.RedisRateLimiter
reject_insecure_bypass_in_production = shared.reject_insecure_bypass_in_production
register_fabric_auth_from_env = shared.register_fabric_auth_from_env


def map_exception_to_contract_detail(
    exc: ValueFabricException,
    *,
    request_id: str,
) -> dict[str, dict[str, object | None]]:
    """Map shared exception primitives to Layer 6 canonical envelope shape."""
    return {
        "error": {
            "code": str(exc.error_code),
            "message": exc.message,
            "request_id": request_id,
            "details": exc.details or None,
        }
    }
