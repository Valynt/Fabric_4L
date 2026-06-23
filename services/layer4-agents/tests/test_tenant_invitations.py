"""Tests for L4 tenant invitation flow (token generation, acceptance, email)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from value_fabric.shared.identity.models import (
    Role,
    UserAcceptInviteRequest,
    UserInviteRequest,
    UserStatus,
)
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class TestInviteUser:
    """Test the enhanced invite_user service function."""

    def _mock_db_with_flush(self, db: AsyncMock) -> None:
        """Set up db.add side-effect to populate created_at/updated_at on User objects."""
        from layer4_agents.tenants.models.user import User

        original_add = db.add

        def _add_side_effect(obj):
            if isinstance(obj, User):
                if obj.created_at is None:
                    obj.created_at = datetime.now(UTC)
                if obj.updated_at is None:
                    obj.updated_at = datetime.now(UTC)
            if original_add.side_effect:
                return original_add.side_effect(obj)
            return None

        db.add = MagicMock(side_effect=_add_side_effect)

    @pytest.mark.asyncio
    async def test_invite_user_generates_token(self):
        """invite_user should generate an invitation token when service is provided."""
        from layer4_agents.tenants.service import invite_user
        from layer4_agents.tenants.invitations import InvitationService

        db = AsyncMock()
        self._mock_db_with_flush(db)
        tenant_id = uuid.uuid4()
        request = UserInviteRequest(email="test@example.com", role=Role.ANALYST)

        # Mock no existing user
        db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        db.flush = AsyncMock()

        invitation_service = InvitationService(redis_client=None)
        user, token = await invite_user(
            db,
            tenant_id,
            request,
            invited_by=uuid.uuid4(),
            inviter_roles=["tenant_admin"],
            invitation_service=invitation_service,
        )

        assert user.email == "test@example.com"
        assert user.role == "analyst"
        assert user.status == "invited"
        assert len(token) > 0  # Token was generated

    @pytest.mark.asyncio
    async def test_invite_user_without_service_returns_empty_token(self):
        """invite_user should return empty token when no invitation_service provided."""
        from layer4_agents.tenants.service import invite_user

        db = AsyncMock()
        self._mock_db_with_flush(db)
        tenant_id = uuid.uuid4()
        request = UserInviteRequest(email="test@example.com", role=Role.ANALYST)

        db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )
        db.flush = AsyncMock()

        user, token = await invite_user(
            db,
            tenant_id,
            request,
            invited_by=uuid.uuid4(),
            inviter_roles=["tenant_admin"],
            invitation_service=None,
        )

        assert token == ""

    @pytest.mark.asyncio
    async def test_invite_user_role_escalation_blocked(self):
        """invite_user should block role escalation."""
        from layer4_agents.tenants.service import invite_user

        db = AsyncMock()
        tenant_id = uuid.uuid4()
        request = UserInviteRequest(email="test@example.com", role=Role.TENANT_ADMIN)

        with pytest.raises(AuthorizationError):
            await invite_user(
                db,
                tenant_id,
                request,
                invited_by=uuid.uuid4(),
                inviter_roles=["analyst"],
            )

    @pytest.mark.asyncio
    async def test_invite_user_duplicate_email_blocked(self):
        """invite_user should block duplicate emails across tenants."""
        from layer4_agents.tenants.service import invite_user

        db = AsyncMock()
        tenant_id = uuid.uuid4()
        request = UserInviteRequest(email="existing@example.com", role=Role.ANALYST)

        existing_user = MagicMock()
        existing_user.email = "existing@example.com"
        db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_user))
        )

        with pytest.raises(ConflictError):
            await invite_user(
                db,
                tenant_id,
                request,
                invited_by=uuid.uuid4(),
                inviter_roles=["tenant_admin"],
            )


class TestAcceptInvitation:
    """Test the accept_invitation service function."""

    @pytest.mark.asyncio
    async def test_accept_invitation_invalid_token(self):
        """accept_invitation should reject invalid tokens."""
        from layer4_agents.tenants.service import accept_invitation
        from layer4_agents.tenants.invitations import InvitationService

        db = AsyncMock()
        invitation_service = InvitationService(redis_client=None)
        request = UserAcceptInviteRequest(token="invalid", password="SecurePass123!")

        with pytest.raises(ValidationError, match="Invalid or expired invitation token"):
            await accept_invitation(db, request, invitation_service)

    @pytest.mark.asyncio
    async def test_accept_invitation_user_not_found(self):
        """accept_invitation should reject if user not found."""
        from layer4_agents.tenants.service import accept_invitation
        from layer4_agents.tenants.invitations import InvitationService

        db = AsyncMock()
        invitation_service = InvitationService(redis_client=None)
        request = UserAcceptInviteRequest(token="test_token", password="SecurePass123!")

        # Mock verify_token to return valid data
        mock_token_data = MagicMock()
        mock_token_data.user_id = str(uuid.uuid4())
        mock_token_data.tenant_id = str(uuid.uuid4())
        invitation_service.verify_token = AsyncMock(return_value=mock_token_data)

        # Mock user not found
        db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        with pytest.raises(NotFoundError, match="Invitation user not found"):
            await accept_invitation(db, request, invitation_service)

    @pytest.mark.asyncio
    async def test_accept_invitation_already_accepted(self):
        """accept_invitation should reject if already accepted."""
        from layer4_agents.tenants.service import accept_invitation
        from layer4_agents.tenants.invitations import InvitationService

        db = AsyncMock()
        invitation_service = InvitationService(redis_client=None)
        request = UserAcceptInviteRequest(token="test_token", password="SecurePass123!")

        mock_token_data = MagicMock()
        mock_token_data.user_id = str(uuid.uuid4())
        mock_token_data.tenant_id = str(uuid.uuid4())
        invitation_service.verify_token = AsyncMock(return_value=mock_token_data)

        # Mock user with active status (not invited)
        existing_user = MagicMock()
        existing_user.status = "active"
        db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=existing_user))
        )

        with pytest.raises(ConflictError, match="Invitation already accepted"):
            await accept_invitation(db, request, invitation_service)

    @pytest.mark.asyncio
    async def test_accept_invitation_success(self):
        """accept_invitation should activate user and hash password on success."""
        from layer4_agents.tenants.service import accept_invitation
        from layer4_agents.tenants.invitations import InvitationService

        db = AsyncMock()
        db.flush = AsyncMock()
        invitation_service = InvitationService(redis_client=None)
        request = UserAcceptInviteRequest(
            token="valid_token", password="SecurePass123!", display_name="New User"
        )

        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        mock_token_data = MagicMock()
        mock_token_data.user_id = user_id
        mock_token_data.tenant_id = tenant_id
        invitation_service.verify_token = AsyncMock(return_value=mock_token_data)
        invitation_service.mark_token_used = AsyncMock()

        # Mock invited user
        invited_user = MagicMock()
        invited_user.id = user_id
        invited_user.tenant_id = tenant_id
        invited_user.email = "invited@example.com"
        invited_user.display_name = None
        invited_user.role = "analyst"
        invited_user.status = UserStatus.INVITED.value
        invited_user.hashed_password = None
        invited_user.invited_by = None
        invited_user.last_login_at = None
        invited_user.created_at = datetime.now(UTC)
        invited_user.updated_at = datetime.now(UTC)
        db.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=invited_user))
        )

        result = await accept_invitation(db, request, invitation_service)

        assert invited_user.status == UserStatus.ACTIVE.value
        assert invited_user.hashed_password is not None
        assert invited_user.display_name == "New User"
        invitation_service.mark_token_used.assert_awaited_once_with("valid_token")


class TestInvitationService:
    """Test InvitationService token management."""

    def test_generate_token_returns_urlsafe_string(self):
        """generate_token should return a URL-safe token."""
        from layer4_agents.tenants.invitations import InvitationService

        service = InvitationService(redis_client=None)
        token = service.generate_token(
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            email="test@example.com",
        )
        assert len(token) > 20
        assert " " not in token

    @pytest.mark.asyncio
    async def test_verify_token_without_redis_returns_none(self):
        """verify_token should return None when Redis is not available."""
        from layer4_agents.tenants.invitations import InvitationService

        service = InvitationService(redis_client=None)
        result = await service.verify_token("any_token")
        assert result is None

    @pytest.mark.asyncio
    async def test_mark_token_used_without_redis_is_noop(self):
        """mark_token_used should be a no-op when Redis is not available."""
        from layer4_agents.tenants.invitations import InvitationService

        service = InvitationService(redis_client=None)
        await service.mark_token_used("any_token")  # Should not raise


class TestPasswordHashing:
    """Test password hashing utilities (bcrypt or sha256_crypt fallback)."""

    def test_hash_password_produces_hash(self):
        """hash_password should produce a non-empty hash."""
        from layer4_agents.tenants.passwords import hash_password

        hashed = hash_password("SecurePass123!")
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """verify_password should return True for correct password."""
        from layer4_agents.tenants.passwords import hash_password, verify_password

        hashed = hash_password("SecurePass123!")
        assert verify_password("SecurePass123!", hashed) is True

    def test_verify_password_incorrect(self):
        """verify_password should return False for incorrect password."""
        from layer4_agents.tenants.passwords import hash_password, verify_password

        hashed = hash_password("SecurePass123!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_password_rejects_sha256_legacy(self):
        """verify_password should reject legacy sha256$ hashes."""
        from layer4_agents.tenants.passwords import verify_password

        assert verify_password("password", "sha256$deadbeef") is False

    def test_hash_password_rejects_too_long(self):
        """hash_password should reject passwords exceeding 72 bytes when bcrypt is active."""
        from layer4_agents.tenants.passwords import hash_password, PasswordTooLongError

        # Only enforce the limit when bcrypt is the active scheme
        import os
        use_bcrypt = os.getenv("USE_BCRYPT", "true").lower() == "true"
        long_password = "a" * 100
        if use_bcrypt:
            # Check if bcrypt actually works in this environment
            try:
                from passlib.context import CryptContext
                ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
                ctx.hash("probe")
            except Exception:
                use_bcrypt = False  # Fallback active — skip length check

        if use_bcrypt:
            with pytest.raises(PasswordTooLongError):
                hash_password(long_password)
        else:
            # Fallback scheme (sha256_crypt) allows longer passwords
            hashed = hash_password(long_password)
            assert len(hashed) > 0
