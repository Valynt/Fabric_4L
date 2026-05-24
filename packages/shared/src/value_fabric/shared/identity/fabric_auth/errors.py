"""Sanitized error taxonomy for the Fabric4L internal AuthContext envelope.

Error messages are intentionally generic. Detailed reasons are logged
server-side; clients only ever see the stable code + a generic message.
"""
from __future__ import annotations


class FabricAuthError(Exception):
    """Base class for envelope-related authentication failures."""

    code: str = "auth.error"
    http_status: int = 401
    public_message: str = "Authentication required."

    def __init__(self, *, log_detail: str | None = None) -> None:
        super().__init__(log_detail or self.public_message)
        self.log_detail = log_detail


class EnvelopeMissingError(FabricAuthError):
    code = "auth.envelope_missing"
    http_status = 401
    public_message = "Authentication required."


class EnvelopeInvalidError(FabricAuthError):
    code = "auth.envelope_invalid"
    http_status = 401
    public_message = "Authentication required."


class EnvelopeExpiredError(FabricAuthError):
    code = "auth.envelope_expired"
    http_status = 401
    public_message = "Authentication required."


class TenantMismatchError(FabricAuthError):
    code = "auth.tenant_mismatch"
    http_status = 403
    public_message = "You do not have access to this resource."
