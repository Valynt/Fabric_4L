"""Invitation token service for tenant user invitations.

Generates secure invitation tokens, stores them in Redis with expiry,
and sends invitation emails via SendGrid or SMTP.
"""

from __future__ import annotations

import asyncio
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import httpx
import redis

from .email_verification import EmailConfig

logger = logging.getLogger(__name__)

DEFAULT_INVITE_TOKEN_EXPIRY_HOURS = 168  # 7 days
MIN_INVITE_TOKEN_EXPIRY_HOURS = 1
MAX_INVITE_TOKEN_EXPIRY_HOURS = 720  # 30 days


@dataclass
class InvitationToken:
    """Verified invitation token data."""

    tenant_id: UUID
    user_id: UUID
    email: str
    token: str
    expires_at: datetime
    used: bool = False


class InvitationService:
    """Service for managing user invitation tokens and emails."""

    def __init__(self, redis_client: redis.Redis | None = None, token_expiry_hours: int = DEFAULT_INVITE_TOKEN_EXPIRY_HOURS) -> None:
        self.redis = redis_client
        self.config = EmailConfig.from_env()
        self.token_expiry_hours = max(
            MIN_INVITE_TOKEN_EXPIRY_HOURS,
            min(token_expiry_hours, MAX_INVITE_TOKEN_EXPIRY_HOURS),
        )

    def generate_token(self, tenant_id: UUID, user_id: UUID, email: str) -> str:
        """Generate and store an invitation token.

        Returns the token string that can be sent to the invitee.
        """
        token = secrets.token_urlsafe(32)
        key = f"invite:{token}"
        data = {
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "email": email,
            "expires": (
                datetime.now(UTC) + timedelta(hours=self.token_expiry_hours)
            ).isoformat(),
            "used": False,
        }

        if self.redis:
            try:
                self.redis.setex(
                    key,
                    int(timedelta(hours=self.token_expiry_hours).total_seconds()),
                    json.dumps(data),
                )
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.warning("Failed to store invitation token in Redis: %s", e)

        return token

    async def verify_token(self, token: str) -> InvitationToken | None:
        """Atomically verify and consume an invitation token.

        Uses Redis GETDEL so that the token is consumed in a single round-trip,
        preventing TOCTOU race conditions where two concurrent requests could
        both read the same valid token before either marks it used.

        Returns None if the token is invalid, expired, or already consumed.
        """
        if not self.redis:
            return None

        key = f"invite:{token}"
        try:
            data = cast(str | None, self.redis.getdel(key))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("Failed to retrieve invitation token from Redis: %s", e)
            return None

        if not data:
            return None

        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return None

        try:
            expires = datetime.fromisoformat(parsed["expires"])
        except (KeyError, ValueError):
            return None

        if datetime.now(UTC) > expires:
            return None

        return InvitationToken(
            tenant_id=UUID(parsed["tenant_id"]),
            user_id=UUID(parsed["user_id"]),
            email=parsed["email"],
            token=token,
            expires_at=expires,
            used=False,
        )

    async def mark_token_used(self, token: str) -> None:
        """Deprecated: token is atomically consumed by ``verify_token`` via GETDEL.

        This method is retained for backward compatibility but is a no-op.
        """
        return

    async def send_invitation_email(
        self,
        to_email: str,
        tenant_name: str,
        inviter_name: str | None,
        invitation_token: str,
        base_url: str = "",
    ) -> bool:
        """Send an invitation email to the invitee.

        Returns True if the email was sent successfully.
        """
        if not base_url:
            base_url = self.config.base_url or "https://fabric4l.example.com"

        accept_url = f"{base_url}/accept-invite?token={invitation_token}"

        subject = f"You've been invited to join {tenant_name} on Fabric 4L"
        inviter_line = f" by {inviter_name}" if inviter_name else ""
        body = f"""Hello,

You've been invited{inviter_line} to join {tenant_name} on Fabric 4L.

Accept your invitation by clicking the link below:
{accept_url}

This link expires in {self.token_expiry_hours // 24} days.

If you didn't expect this invitation, please ignore this email.
"""

        if self.config.sendgrid_api_key:
            return await self._send_sendgrid(to_email, subject, body)
        elif self.config.smtp_host:
            return await self._send_smtp(to_email, subject, body)
        else:
            logger.warning("No email provider configured. Invitation email not sent.")
            # In development mode, log the token for testing
            if self._is_dev_mode():
                logger.info("[DEV MODE] Invitation accept URL: %s", accept_url)
                return True
            return False

    def _is_dev_mode(self) -> bool:
        env = (self.config.environment or "").lower()
        return env in {"development", "dev", "test", "testing"}

    async def _send_sendgrid(self, to_email: str, subject: str, body: str) -> bool:
        """Send via SendGrid API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {self.config.sendgrid_api_key}"},
                    json={
                        "personalizations": [{"to": [{"email": to_email}]}],
                        "from": {"email": self.config.from_address},
                        "subject": subject,
                        "content": [{"type": "text/plain", "value": body}],
                    },
                )
                return response.status_code == 202
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Failed to send invitation email via SendGrid: %s", e)
                return False

    async def _send_smtp(self, to_email: str, subject: str, body: str) -> bool:
        """Send via SMTP (async wrapper)."""
        try:
            import aiosmtplib

            await aiosmtplib.send(
                sender=self.config.from_address,
                recipients=[to_email],
                subject=subject,
                message=body,
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.smtp_user,
                password=self.config.smtp_pass,
                start_tls=True,
            )
            return True
        except ImportError:
            logger.error("aiosmtplib not installed. Cannot send SMTP email.")
            return False
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Failed to send invitation email via SMTP: %s", e)
            return False
