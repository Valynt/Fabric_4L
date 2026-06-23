"""Local adapter boundary for controlled ``value_fabric`` imports.

Service code should import shared/runtime symbols via this module to avoid
accidental deep imports from non-public ``value_fabric`` paths.
"""

from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.error_handling.exceptions import ValueFabricException


def map_exception_to_contract_detail(
    exc: ValueFabricException,
    *,
    request_id: str,
) -> dict[str, dict[str, object | None]]:
    """Map shared exception primitives to the canonical ErrorEnvelope shape."""
    return {
        "error": {
            "code": exc.error_code.value,
            "message": exc.message,
            "request_id": request_id,
            "details": exc.details or None,
        }
    }


__all__ = ["map_exception_to_contract_detail", "register_exception_handlers"]
