from fastapi import Request
import pytest

from layer4_agents.services.billing_security import validate_webhook_request_security
from value_fabric.shared.error_handling.exceptions import AuthorizationError


@pytest.mark.unit
def test_validate_webhook_request_security_uses_canonical_authz_exception() -> None:
    scope = {"type": "http", "headers": [], "client": ("203.0.113.10", 1234)}
    request = Request(scope)
    with pytest.raises(AuthorizationError):
        validate_webhook_request_security(request, "t=1,v1=sig", enforce_ip_check=True)
