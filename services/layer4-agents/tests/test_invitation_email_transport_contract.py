from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

import layer4_agents.tenants.email_verification as email_module
import layer4_agents.tenants.invitations as invitation_module
from layer4_agents.tenants.email_verification import EmailConfig, EmailVerificationService
from layer4_agents.tenants.invitations import InvitationService

TENANT = UUID("550e8400-e29b-41d4-a716-446655440000")
USER = UUID("5f7ed580-763c-4adb-9b4d-4c79e5152548")


class Redis:
    def __init__(self):
        self.values = {}

    def setex(self, key, _expiry, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)


@pytest.mark.asyncio
async def test_invitation_token_lifecycle_and_invalid_payloads() -> None:
    assert await InvitationService().verify_token("missing") is None
    redis = Redis()
    service = InvitationService(redis, token_expiry_hours=1000)
    assert service.token_expiry_hours == 720
    token = service.generate_token(TENANT, USER, "user@example.test")
    verified = await service.verify_token(token)
    assert verified.tenant_id == TENANT and verified.user_id == USER
    await service.consume_token(token)
    assert await service.verify_token(token) is None
    await InvitationService().consume_token(token)
    await service.mark_token_used(token)

    redis.values["invite:bad"] = "not-json"
    assert await service.verify_token("bad") is None
    redis.values["invite:used"] = json.dumps({"used": True})
    assert await service.verify_token("used") is None
    redis.values["invite:malformed"] = json.dumps({"expires": "bad"})
    assert await service.verify_token("malformed") is None
    redis.values["invite:expired"] = json.dumps(
        {
            "tenant_id": str(TENANT),
            "user_id": str(USER),
            "email": "user@example.test",
            "expires": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        }
    )
    assert await service.verify_token("expired") is None


@pytest.mark.asyncio
async def test_invitation_provider_routing_and_dev_mode(monkeypatch) -> None:
    service = InvitationService()
    service.config = EmailConfig(environment="production")
    assert not service._is_dev_mode()
    assert not await service.send_invitation_email("to@test", "Tenant", None, "token")
    service.config = EmailConfig(environment="test")
    assert service._is_dev_mode()
    assert await service.send_invitation_email("to@test", "Tenant", "Inviter", "token")
    service.config = EmailConfig(sendgrid_api_key="key")
    monkeypatch.setattr(service, "_send_sendgrid", lambda *_args: _value(True))
    assert await service.send_invitation_email("to@test", "Tenant", None, "token")
    service.config = EmailConfig(smtp_host="smtp.test")
    monkeypatch.setattr(service, "_send_smtp", lambda *_args: _value(True))
    assert await service.send_invitation_email("to@test", "Tenant", None, "token")


class HTTPClient:
    def __init__(self, status=202, error=None):
        self.status = status
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, *_args, **_kwargs):
        if self.error:
            raise self.error
        return SimpleNamespace(status_code=self.status)


@pytest.mark.asyncio
@pytest.mark.parametrize("module", [email_module, invitation_module])
async def test_sendgrid_success_rejection_and_failure(monkeypatch, module) -> None:
    service = EmailVerificationService() if module is email_module else InvitationService()
    service.config = EmailConfig(sendgrid_api_key="key")
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: HTTPClient(202))
    assert await service._send_sendgrid("to@test", "subject", "body")
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: HTTPClient(400))
    assert not await service._send_sendgrid("to@test", "subject", "body")
    monkeypatch.setattr(
        module.httpx, "AsyncClient", lambda: HTTPClient(error=RuntimeError("network"))
    )
    assert not await service._send_sendgrid("to@test", "subject", "body")


@pytest.mark.asyncio
@pytest.mark.parametrize("service", [EmailVerificationService(), InvitationService()])
async def test_smtp_success_and_failure(monkeypatch, service) -> None:
    calls = []

    async def send(**kwargs):
        calls.append(kwargs)

    monkeypatch.setitem(sys.modules, "aiosmtplib", SimpleNamespace(send=send))
    service.config = EmailConfig(smtp_host="smtp.test", smtp_user="user", smtp_pass="pass")
    assert await service._send_smtp("to@test", "subject", "body")
    assert calls[0]["hostname"] == "smtp.test" and calls[0]["start_tls"]

    async def fail(**_kwargs):
        raise RuntimeError("smtp failure")

    monkeypatch.setitem(sys.modules, "aiosmtplib", SimpleNamespace(send=fail))
    assert not await service._send_smtp("to@test", "subject", "body")


@pytest.mark.asyncio
async def test_email_convenience_function(monkeypatch) -> None:
    monkeypatch.setattr(
        EmailVerificationService,
        "send_verification_email",
        lambda *_args, **_kwargs: _value(True),
    )
    assert await email_module.send_verification_email("to@test", "Tenant", "token")


async def _value(value):
    return value
