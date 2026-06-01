"""Local adapter boundary for controlled ``value_fabric`` imports.

Service code should import shared/runtime symbols via this module to avoid
accidental deep imports from non-public ``value_fabric`` paths.
"""

from value_fabric.shared.error_handling.exceptions import ValueFabricException


def map_exception_to_contract_detail(
    exc: ValueFabricException,
    *,
    request_id: str | None = None,
) -> dict[str, object]:
    """Map shared exception primitives to Layer 4 HTTP detail contract."""
    return {
        "error_code": str(exc.error_code),
        "message": exc.message,
        "request_id": request_id,
        "correlation_id": request_id,
        "details": exc.details,
    }
