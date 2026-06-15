"""Local adapter boundary for controlled ``value_fabric`` imports.

Service code should import shared/runtime symbols via this module to avoid
accidental deep imports from non-public ``value_fabric`` paths.
"""

from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.error_handling.exceptions import ValueFabricException
from value_fabric.shared.error_handling.models import ErrorDetail, ErrorEnvelope


def map_exception_to_contract_detail(
    exc: ValueFabricException,
    *,
    request_id: str | None = None,
) -> dict[str, object]:
    """Map shared exception primitives to Layer 4 HTTP detail contract."""
    envelope = ErrorEnvelope(
        error=ErrorDetail(
            code=exc.error_code,
            message=exc.message,
            request_id=request_id or "unknown",
            details=exc.details,
        )
    )
    return envelope.model_dump()


__all__ = ["map_exception_to_contract_detail", "register_exception_handlers"]
