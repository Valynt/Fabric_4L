"""Local adapter boundary for controlled ``value_fabric`` imports.

Service code should import shared/runtime symbols via this module to avoid
accidental deep imports from non-public ``value_fabric`` paths.
"""

from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.error_handling.exceptions import ValueFabricException


def map_exception_to_http_contract(
    exc: ValueFabricException,
    *,
    request_id: str,
) -> dict[str, dict[str, object | None]]:
    """Map shared exceptions to Layer 5 canonical HTTP handler envelope."""
    return {
        "error": {
            "code": exc.error_code.value,
            "message": exc.message,
            "request_id": request_id,
            "details": None,
        }
    }


def map_exception_to_unhandled_contract() -> dict[str, dict[str, object | None]]:
    """Preserve Layer 5 catch-all semantics for unhandled exceptions."""
    return {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again or contact support.",
            "request_id": None,
            "details": None,
        }
    }


__all__ = [
    "map_exception_to_http_contract",
    "map_exception_to_unhandled_contract",
    "register_exception_handlers",
]
