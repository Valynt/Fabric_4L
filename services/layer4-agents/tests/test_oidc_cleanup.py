from __future__ import annotations

"""Tests for OIDC session cleanup service."""


import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Set required environment variable for shared imports
os.environ["JWT_SECRET"] = "test-secret-123456789012345678901234567890"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from layer4_agents.services.oidc_cleanup import OIDCCleanupTask, cleanup_expired_oidc_sessions


class TestCleanupExpiredSessions:
    """Tests for cleanup_expired_oidc_sessions function."""

    @pytest.mark.asyncio
    async def test_cleanup_deletes_expired_sessions(self):
        """Test that expired sessions are deleted."""
        # Mock result with 2 deleted rows
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("session-1",),
            ("session-2",),
        ]

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        deleted_count = await cleanup_expired_oidc_sessions(db)

        assert deleted_count == 2
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_no_expired_sessions(self):
        """Test when no expired sessions exist."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        deleted_count = await cleanup_expired_oidc_sessions(db)

        assert deleted_count == 0
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_rolls_back_on_error(self):
        """Test that transaction is rolled back on error."""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("Database error"))

        with pytest.raises(Exception, match="Database error"):
            await cleanup_expired_oidc_sessions(db)

        db.rollback.assert_called_once()


class TestOIDCCleanupTask:
    """Tests for OIDCCleanupTask background service."""

    @pytest.mark.asyncio
    async def test_cleanup_task_start_stop(self):
        """Test that cleanup task can be started and stopped."""
        db_factory = MagicMock()

        task = OIDCCleanupTask(
            db_session_factory=db_factory,
            interval_seconds=0.1,  # Short interval for testing
        )

        # Start the task
        await task.start()
        assert task._task is not None

        # Stop the task
        await task.stop()
        assert task._task is None

    @pytest.mark.asyncio
    async def test_cleanup_task_runs_periodically(self):
        """Test that cleanup runs multiple times."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def mock_session():
            return mock_db

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        task = OIDCCleanupTask(
            db_session_factory=mock_factory,
            interval_seconds=0.05,  # Very short for testing
        )

        await task.start()

        # Let it run for a short time
        await asyncio.sleep(0.15)

        await task.stop()

        # Should have executed cleanup multiple times
        assert mock_db.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_cleanup_task_handles_errors_gracefully(self):
        """Test that task continues running after errors."""
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("DB Error"))

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        task = OIDCCleanupTask(
            db_session_factory=mock_factory,
            interval_seconds=0.05,
        )

        await task.start()

        # Let it run briefly - should not crash
        await asyncio.sleep(0.12)

        await task.stop()

        # Should have attempted cleanup at least once
        assert mock_db.execute.call_count >= 1

    @pytest.mark.asyncio
    async def test_cleanup_task_marks_system_db_bypass(self, monkeypatch):
        """Background cleanup should explicitly mark system DB sessions as bypass."""
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        clear_context = AsyncMock()
        monkeypatch.setattr(
            "layer4_agents.services.oidc_cleanup._clear_local_tenant_context",
            clear_context,
        )

        task = OIDCCleanupTask(
            db_session_factory=mock_factory,
            interval_seconds=0.05,
        )

        await task.start()
        await asyncio.sleep(0.08)
        await task.stop()

        clear_context.assert_awaited()


# Import asyncio at the end to avoid issues with the test file
import asyncio
