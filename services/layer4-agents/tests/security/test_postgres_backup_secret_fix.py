"""P0-007: Postgres backup cronjob must reference only existing secret keys.

The postgres-backup CronJob previously tried to read ``username`` from
``postgres-secret``, but that secret only contains ``password``.
The fix hardcodes POSTGRES_USER and only reads the password from the secret.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def _project_root() -> Path:
    # services/layer4-agents/tests/security/test_*.py -> project root
    return Path(__file__).resolve().parents[4]


def _load_cronjob():
    path = _project_root() / "k8s" / "base" / "postgres-backup-cronjob.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_secret():
    path = _project_root() / "k8s" / "secrets.yml"
    with open(path, encoding="utf-8") as f:
        docs = list(yaml.safe_load_all(f))
    for doc in docs:
        if doc and doc.get("metadata", {}).get("name") == "postgres-secret":
            return doc
    return None


class TestPostgresBackupSecretReferences:
    """Backup cronjob secret references must be valid."""

    def test_postgres_secret_has_password_key(self):
        secret = _load_secret()
        assert secret is not None, "postgres-secret must exist in k8s/secrets.yml"
        data = secret.get("stringData") or secret.get("data") or {}
        assert "password" in data, "postgres-secret must contain 'password' key"

    def test_backup_cronjob_does_not_reference_missing_username_key(self):
        cronjob = _load_cronjob()
        container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]
        env = container.get("env", [])

        for entry in env:
            if entry.get("name") == "POSTGRES_USER":
                # Must be hardcoded, not sourced from secret key "username"
                assert "valueFrom" not in entry, (
                    "POSTGRES_USER must not be sourced from a secretKeyRef; "
                    "postgres-secret does not contain a 'username' key"
                )
                assert entry.get("value") == "postgres", (
                    "POSTGRES_USER should be hardcoded to 'postgres'"
                )
                return

        raise AssertionError("POSTGRES_USER env var not found in backup cronjob")

    def test_backup_cronjob_reads_password_from_correct_secret(self):
        cronjob = _load_cronjob()
        container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]
        env = container.get("env", [])

        password_entry = next(
            (e for e in env if e.get("name") == "POSTGRES_PASSWORD"), None
        )
        assert password_entry is not None, "POSTGRES_PASSWORD env var must exist"
        assert "valueFrom" in password_entry, "POSTGRES_PASSWORD must be sourced from a secret"
        secret_ref = password_entry["valueFrom"]["secretKeyRef"]
        assert secret_ref["name"] == "postgres-secret", (
            f"Expected secret name 'postgres-secret', got '{secret_ref['name']}'"
        )
        assert secret_ref["key"] == "password", (
            f"Expected secret key 'password', got '{secret_ref['key']}'"
        )

    def test_backup_cronjob_has_no_inline_secrets(self):
        cronjob = _load_cronjob()
        container = cronjob["spec"]["jobTemplate"]["spec"]["template"]["spec"]["containers"][0]
        env = container.get("env", [])

        for entry in env:
            if entry.get("name") in {"POSTGRES_PASSWORD", "PGPASSWORD"}:
                assert "value" not in entry or entry.get("value") == "", (
                    f"{entry['name']} must not contain an inline secret value"
                )
