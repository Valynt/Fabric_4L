from __future__ import annotations

"""Email verification service for tenant registration."""
import asyncio
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TOKEN_EXPIRY_HOURS = 24
MIN_TOKEN_EXPIRY_HOURS = 1
MAX_TOKEN_EXPIRY_HOURS = 168  # 7 days
SMTP_PORT_MIN = 1
SMTP_PORT_MAX = 65535


class EmailConfig(BaseModel):
    """Email service configuration."""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    from_address: str = "noreply@fabric4l.example.com"

    # Or use external service (SendGrid, etc.)
    sendgrid_api_key: str = ""

    # Application base URL for link generation
    base_url: str = ""

    # Runtime environment (development, production, etc.)
    environment: str = ""

    @field_validator("smtp_port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate SMTP port is in valid range."""
        if not SMTP_PORT_MIN <= v <= SMTP_PORT_MAX:
            raise ValueError(f"SMTP port must be between {SMTP_PORT_MIN} and {SMTP_PORT_MAX}")
        return v

    @classmethod
    def from_env(cls) -> EmailConfig:
        port_str = os.getenv("SMTP_PORT", "587")
        try:
            port = int(port_str)
        except ValueError:
            logger.warning(f"Invalid SMTP_PORT value: {port_str}, using default 587")
            port = 587

        return cls(
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=port,
            smtp_user=os.getenv("SMTP_USER", ""),
            smtp_pass=os.getenv("SMTP_PASS", ""),
            from_address=os.getenv("EMAIL_FROM", "noreply@fabric4l.example.com"),
            sendgrid_api_key=os.getenv("SENDGRID_API_KEY", ""),
            base_url=os.getenv("APP_BASE_URL", ""),
            environment=os.getenv("ENVIRONMENT", "production"),
        )


@dataclass
class VerificationToken:
    """Email verification token."""

    tenant_id: UUID
    email: str
    token: str
    expires_at: datetime
    used: bool = False


class EmailVerificationService:
    """Service for email verification."""

    def __init__(self, redis_client=None, token_expiry_hours: int = DEFAULT_TOKEN_EXPIRY_HOURS) -> None:
        self.redis = redis_client
        self.config = EmailConfig.from_env()
        # Clamp expiry to valid range
        self.token_expiry_hours = max(MIN_TOKEN_EXPIRY_HOURS, min(token_expiry_hours, MAX_TOKEN_EXPIRY_HOURS))

    def generate_token(self, tenant_id: UUID, email: str) -> str:
        """Generate and store verification token."""
        token = secrets.token_urlsafe(32)

        # Store in Redis with expiry if available
        key = f"email_verification:{token}"
        data = {
            "tenant_id": str(tenant_id),
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
                logger.warning(f"Failed to store verification token in Redis: {e}")

        return token

    async def verify_token(self, token: str) -> VerificationToken | None:
        """Verify a token and return tenant info."""
        if not self.redis:
            return None

        key = f"email_verification:{token}"
        try:
            data = self.redis.get(key)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Failed to retrieve verification token from Redis: {e}")
            return None

        if not data:
            return None

        try:
            parsed = json.loads(data)
        except json.JSONDecodeError:
            return None

        if parsed.get("used"):
            return None

        try:
            expires = datetime.fromisoformat(parsed["expires"])
        except (KeyError, ValueError):
            return None

        if datetime.now(UTC) > expires:
            return None

        return VerificationToken(
            tenant_id=UUID(parsed["tenant_id"]),
            email=parsed["email"],
            token=token,
            expires_at=expires,
            used=parsed.get("used", False),
        )

    async def mark_token_used(self, token: str) -> None:
        """Mark token as used after verification."""
        if not self.redis:
            return

        key = f"email_verification:{token}"
        try:
            data_str = self.redis.get(key)
            if data_str:
                data = json.loads(data_str)
                data["used"] = True
                self.redis.setex(key, 3600, json.dumps(data))  # Keep for 1 hour
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"Failed to mark verification token as used: {e}")

    async def send_verification_email(
        self,
        to_email: str,
        tenant_name: str,
        verification_token: str,
        base_url: str = "",
    ) -> bool:
        """Send verification email."""
        if not base_url:
            base_url = os.getenv("APP_BASE_URL", "https://fabric4l.example.com")

        verify_url = f"{base_url}/api/v1/tenants/verify-email?token={verification_token}"

        subject = f"Verify your email for {tenant_name}"
        expiry_hours = self.token_expiry_hours if hasattr(self, 'token_expiry_hours') else DEFAULT_TOKEN_EXPIRY_HOURS
        body = f"""Welcome to Fabric 4L!

Please verify your email by clicking the link below:
{verify_url}

This link expires in {expiry_hours} hours.

If you didn't request this, please ignore this email.
"""

        if self.config.sendgrid_api_key:
            return await self._send_sendgrid(to_email, subject, body)
        elif self.config.smtp_host:
            return await self._send_smtp(to_email, subject, body)
        else:
            logger.warning("No email provider configured. Email not sent.")
            # In development mode, log the token for testing
            if os.getenv("ENVIRONMENT", "production").lower() == "development":
                logger.info(f"[DEV MODE] Verification URL: {verify_url}")
                return True
            return False

    async def _send_sendgrid(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> bool:
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
                logger.error(f"Failed to send email via SendGrid: {e}")
                return False

    async def _send_smtp(
        self,
        to_email: str,
        subject: str,
        body: str,
    ) -> bool:
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
            logger.error(f"Failed to send email via SMTP: {e}")
            return False


# Convenience function


async def send_verification_email(
    to_email: str,
    tenant_name: str,
    token: str,
    base_url: str = "",
) -> bool:
    """Convenience function to send verification email."""
    service = EmailVerificationService()
    return await service.send_verification_email(to_email, tenant_name, token, base_url)
