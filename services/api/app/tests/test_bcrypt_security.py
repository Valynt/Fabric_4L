"""
Bcrypt security tests - verify production password hashing behavior.

These tests verify critical security features:
1. Password length validation (72-byte limit)
2. Production guard preventing USE_BCRYPT=false in production
3. Thread-safe initialization
"""

from __future__ import annotations

import os
import pytest

from app.core.security import (
    MAX_BCRYPT_PASSWORD_BYTES,
    PasswordTooLongError,
    hash_password,
    verify_password,
    get_pwd_context,
)


class TestPasswordLengthValidation:
    """Tests for the 72-byte password limit enforcement."""

    def test_password_over_72_bytes_rejected(self) -> None:
        """Verify passwords over 72 bytes are rejected with PasswordTooLongError."""
        import app.core.security as security_mod
        
        # Temporarily enable bcrypt to test the limit
        old_use_bcrypt = os.getenv("USE_BCRYPT")
        os.environ["USE_BCRYPT"] = "true"
        security_mod._pwd_context = None
        
        try:
            pwd = "a" * 73  # Over limit
            with pytest.raises(PasswordTooLongError) as exc_info:
                hash_password(pwd)
            assert exc_info.value.length == 73
            assert exc_info.value.max_length == MAX_BCRYPT_PASSWORD_BYTES
        finally:
            if old_use_bcrypt is None:
                os.environ.pop("USE_BCRYPT", None)
            else:
                os.environ["USE_BCRYPT"] = old_use_bcrypt
            security_mod._pwd_context = None

    @pytest.mark.skip(reason="Requires compatible bcrypt library version")
    def test_password_exactly_72_bytes_accepted(self) -> None:
        """Verify passwords exactly at 72-byte limit are accepted."""
        import app.core.security as security_mod
        
        # Temporarily enable bcrypt to test the limit
        old_use_bcrypt = os.getenv("USE_BCRYPT")
        os.environ["USE_BCRYPT"] = "true"
        security_mod._pwd_context = None
        
        try:
            pwd = "a" * 72  # Exactly at limit
            hashed = hash_password(pwd)
            assert hashed is not None
            assert verify_password(pwd, hashed)
        finally:
            if old_use_bcrypt is None:
                os.environ.pop("USE_BCRYPT", None)
            else:
                os.environ["USE_BCRYPT"] = old_use_bcrypt
            security_mod._pwd_context = None

    @pytest.mark.skip(reason="Requires compatible bcrypt library version")
    def test_password_within_72_bytes_accepted(self) -> None:
        """Verify passwords within 72-byte limit are accepted."""
        import app.core.security as security_mod
        
        # Temporarily enable bcrypt to test the limit
        old_use_bcrypt = os.getenv("USE_BCRYPT")
        os.environ["USE_BCRYPT"] = "true"
        security_mod._pwd_context = None
        
        try:
            pwd = "a" * 71  # Within limit
            hashed = hash_password(pwd)
            assert hashed is not None
            assert verify_password(pwd, hashed)
        finally:
            if old_use_bcrypt is None:
                os.environ.pop("USE_BCRYPT", None)
            else:
                os.environ["USE_BCRYPT"] = old_use_bcrypt
            security_mod._pwd_context = None

    def test_no_silent_truncation_vulnerability(self) -> None:
        """Verify two different over-72-byte passwords with same prefix cannot both hash.
        
        This test ensures that if someone tries to bypass the limit by using
        passwords that share the first 72 bytes, they cannot both authenticate
        (since we reject before hashing, not after truncation).
        """
        import app.core.security as security_mod
        
        # Temporarily enable bcrypt to test the limit
        old_use_bcrypt = os.getenv("USE_BCRYPT")
        os.environ["USE_BCRYPT"] = "true"
        security_mod._pwd_context = None
        
        try:
            pwd1 = "a" * 73  # "a" * 72 + "a"
            pwd2 = "a" * 72 + "b"  # "a" * 72 + "b"
            
            # Both should be rejected
            with pytest.raises(PasswordTooLongError):
                hash_password(pwd1)
            with pytest.raises(PasswordTooLongError):
                hash_password(pwd2)
        finally:
            if old_use_bcrypt is None:
                os.environ.pop("USE_BCRYPT", None)
            else:
                os.environ["USE_BCRYPT"] = old_use_bcrypt
            security_mod._pwd_context = None

    def test_unicode_password_byte_length_enforced(self) -> None:
        """Verify password limit is enforced on byte length, not character count.
        
        Unicode characters can be multiple bytes, so a password with few characters
        but many bytes should still be rejected if it exceeds 72 bytes.
        """
        import app.core.security as security_mod
        
        # Temporarily enable bcrypt to test the limit
        old_use_bcrypt = os.getenv("USE_BCRYPT")
        os.environ["USE_BCRYPT"] = "true"
        security_mod._pwd_context = None
        
        try:
            # Emoji can be 4 bytes each
            pwd = "😀" * 20  # 20 * 4 = 80 bytes (over limit)
            with pytest.raises(PasswordTooLongError):
                hash_password(pwd)
        finally:
            if old_use_bcrypt is None:
                os.environ.pop("USE_BCRYPT", None)
            else:
                os.environ["USE_BCRYPT"] = old_use_bcrypt
            security_mod._pwd_context = None


class TestProductionGuard:
    """Tests for the production guard that prevents USE_BCRYPT=false in production."""

    def test_use_bcrypt_false_rejected_in_production(self) -> None:
        """Verify USE_BCRYPT=false raises RuntimeError in production-like environments."""
        import app.core.security as security_mod
        
        # Test each production-like environment
        for env in ["production", "prod", "staging", "stage", "preprod", "pre-production"]:
            old_env = os.getenv("ENVIRONMENT")
            old_use_bcrypt = os.getenv("USE_BCRYPT")
            
            try:
                os.environ["ENVIRONMENT"] = env
                os.environ["USE_BCRYPT"] = "false"
                security_mod._pwd_context = None  # Force re-initialization
                
                with pytest.raises(RuntimeError) as exc_info:
                    get_pwd_context()
                
                assert "USE_BCRYPT=false is not allowed" in str(exc_info.value)
                assert "production-like environments" in str(exc_info.value)
            finally:
                # Restore original values
                if old_env is None:
                    os.environ.pop("ENVIRONMENT", None)
                else:
                    os.environ["ENVIRONMENT"] = old_env
                if old_use_bcrypt is None:
                    os.environ.pop("USE_BCRYPT", None)
                else:
                    os.environ["USE_BCRYPT"] = old_use_bcrypt
                security_mod._pwd_context = None


class TestThreadSafety:
    """Tests for thread-safe lazy initialization."""

    def test_concurrent_initialization_returns_same_context(self) -> None:
        """Verify multiple concurrent calls to get_pwd_context return the same context."""
        import threading
        import app.core.security as security_mod
        
        # Reset context
        security_mod._pwd_context = None
        
        contexts = []
        errors = []
        
        def get_context():
            try:
                ctx = get_pwd_context()
                contexts.append(ctx)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = [threading.Thread(target=get_context) for _ in range(10)]
        
        # Start all threads
        for t in threads:
            t.start()
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Errors occurred: {errors}"
        
        # Verify all threads got the same context
        assert len(contexts) == 10
        assert all(ctx is contexts[0] for ctx in contexts)
