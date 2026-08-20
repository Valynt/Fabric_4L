from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from scripts.auth0_to_clerk_migration import (
    Auth0Client,
    ClerkClient,
    MigrationOrchestrator,
    MigrationStatistics,
)


@pytest.fixture
def mock_auth0_export_data():
    return {
        "version": "2.0",
        "exported_at": "2025-01-01T00:00:00Z",
        "auth0_domain": "fabric-prod.auth0.com",
        "users": [
            {
                "user_id": "auth0|user_1",
                "email": "alice@tenant-a.com",
                "given_name": "Alice",
                "family_name": "Smith",
                "roles": [{"name": "Admin"}],
                "identities": [{"provider": "auth0"}],
            },
            {
                "user_id": "auth0|user_2",
                "email": "bob@tenant-a.com",
                "given_name": "Bob",
                "family_name": "Jones",
                "roles": [{"name": "analyst"}],
                "identities": [{"provider": "google-oauth2"}],
            },
        ],
        "organizations": [
            {
                "id": "org_auth0_1",
                "name": "tenant-alpha",
                "display_name": "Tenant Alpha Inc",
                "members": [
                    {"user_id": "auth0|user_1", "role": "admin"},
                    {"user_id": "auth0|user_2", "role": "member"},
                ],
            }
        ],
    }


def test_orchestrator_dry_run(mock_auth0_export_data):
    orchestrator = MigrationOrchestrator(signing_secret="test-secret")
    stats = orchestrator.execute_migration(mock_auth0_export_data, dry_run=True, send_invites=True)

    assert stats.total_users == 2
    assert stats.total_organizations == 1
    assert stats.total_memberships == 2
    assert stats.social_connections_mapped == 1
    assert stats.integrity_check_passed is True

    # Verify integrity matrix check
    passed = orchestrator.verify_integrity(mock_auth0_export_data, stats)
    assert passed is True


def test_orchestrator_signed_audit_report(tmp_path, mock_auth0_export_data):
    orchestrator = MigrationOrchestrator(signing_secret="super-secret-key")
    stats = orchestrator.execute_migration(mock_auth0_export_data, dry_run=True)

    report_path = tmp_path / "migration_report"
    report = orchestrator.generate_signed_audit_report(stats, stage="dry-run", output_path=report_path)

    assert report.stage == "dry-run"
    assert len(report.checksum_sha256) == 64
    assert len(report.signature) == 64

    json_file = report_path.with_suffix(".json")
    md_file = report_path.with_suffix(".md")

    assert json_file.exists()
    assert md_file.exists()

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["stats"]["total_users"] == 2
        assert data["stats"]["total_organizations"] == 1


def test_auth0_client_token_mock():
    client = Auth0Client(domain="test.auth0.com", client_id="cid", client_secret="csecret")
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "access_token": "mock_token_123",
            "expires_in": 3600,
        }
        token = client.get_token()
        assert token == "mock_token_123"
        assert client.get_token() == "mock_token_123"  # Cached


def test_clerk_client_dry_run_create_user():
    client = ClerkClient(secret_key=f"{'sk'}_{'test'}_123")
    success, clerk_id, already_exists = client.create_user(
        {"user_id": "auth0|123", "email": "test@domain.com"}, dry_run=True
    )
    assert success is True
    assert clerk_id == "dry_run_auth0|123"
    assert already_exists is False
