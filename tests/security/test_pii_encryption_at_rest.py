"""Security regression tests for P1-003: PII Encryption at Rest.

Validates that confirmed sensitive fields use EncryptedString and that
searchable PII fields maintain a blind index for exact-match lookups.
"""

from __future__ import annotations

import ast
from pathlib import Path


class TestEncryptedColumnExists:
    """The shared crypto package must expose EncryptedString and blind_index."""

    def test_encrypted_string_exported(self) -> None:
        from value_fabric.shared.crypto import EncryptedString

        assert EncryptedString is not None

    def test_blind_index_exported(self) -> None:
        from value_fabric.shared.crypto import blind_index

        assert blind_index is not None

    def test_encrypted_string_is_type_decorator(self) -> None:
        from sqlalchemy.types import TypeDecorator
        from value_fabric.shared.crypto import EncryptedString

        assert issubclass(EncryptedString, TypeDecorator)


class TestModelFieldsUseEncryptedString:
    """Confirmed PII fields must use EncryptedString instead of plain String."""

    def _model_source(self, rel_path: str) -> str:
        root = Path(__file__).resolve().parents[2]
        return (root / rel_path).read_text(encoding="utf-8")

    def _has_encrypted_column(self, source: str, field_name: str) -> bool:
        """Check that a field assignment uses EncryptedString()."""
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id == field_name:
                    # Walk the RHS looking for EncryptedString() call
                    for child in ast.walk(node.annotation):
                        if isinstance(child, ast.Constant) and child.value == "encrypted":
                            return True
                    for child in ast.walk(node.value):
                        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                            if child.func.id == "EncryptedString":
                                return True
        return False

    def test_account_owner_email_is_encrypted(self) -> None:
        src = self._model_source("services/layer4-agents/src/models/account.py")
        assert self._has_encrypted_column(src, "owner_email"), (
            "Account.owner_email must use EncryptedString"
        )

    def test_account_headquarters_is_encrypted(self) -> None:
        src = self._model_source("services/layer4-agents/src/models/account.py")
        assert self._has_encrypted_column(src, "headquarters"), (
            "Account.headquarters must use EncryptedString"
        )

    def test_billing_customer_email_is_encrypted(self) -> None:
        src = self._model_source("services/layer4-agents/src/models/billing.py")
        assert self._has_encrypted_column(src, "email"), (
            "BillingCustomer.email must use EncryptedString"
        )

    def test_billing_customer_name_is_encrypted(self) -> None:
        src = self._model_source("services/layer4-agents/src/models/billing.py")
        assert self._has_encrypted_column(src, "name"), (
            "BillingCustomer.name must use EncryptedString"
        )

    def test_user_email_is_encrypted(self) -> None:
        src = self._model_source("services/layer4-agents/src/tenants/models/user.py")
        assert self._has_encrypted_column(src, "email"), (
            "User.email must use EncryptedString"
        )


class TestSearchablePiiHasBlindIndex:
    """Searchable PII fields must have a companion blind-index column."""

    def test_user_has_email_hash_column(self) -> None:
        src = Path("services/layer4-agents/src/tenants/models/user.py").read_text(
            encoding="utf-8"
        )
        assert "email_hash" in src, "User model must define email_hash for blind-index lookups"

    def test_user_unique_constraint_uses_email_hash(self) -> None:
        src = Path("services/layer4-agents/src/tenants/models/user.py").read_text(
            encoding="utf-8"
        )
        assert 'UniqueConstraint("tenant_id", "email_hash"' in src, (
            "User unique constraint must use email_hash, not plaintext email"
        )

    def test_oidc_query_uses_email_hash(self) -> None:
        src = Path("services/layer4-agents/src/tenants/api/routes/oidc.py").read_text(
            encoding="utf-8"
        )
        assert "email_hash" in src, (
            "_get_user_by_email must query by email_hash blind index"
        )
        assert "blind_index(email)" in src, (
            "_get_user_by_email must compute blind_index(email) for the lookup"
        )


class TestMigrationExists:
    """A migration must exist that adds the email_hash column."""

    def test_migration_file_exists(self) -> None:
        migrations_dir = Path("services/layer4-agents/migrations/versions")
        files = list(migrations_dir.glob("*add_user_email_hash*"))
        assert len(files) >= 1, (
            "Expected a migration adding email_hash to users table"
        )

    def test_migration_adds_email_hash_column(self) -> None:
        migrations_dir = Path("services/layer4-agents/migrations/versions")
        file = list(migrations_dir.glob("*add_user_email_hash*"))[0]
        src = file.read_text(encoding="utf-8")
        assert 'op.add_column("users", sa.Column("email_hash"' in src

    def test_migration_replaces_unique_constraint(self) -> None:
        migrations_dir = Path("services/layer4-agents/migrations/versions")
        file = list(migrations_dir.glob("*add_user_email_hash*"))[0]
        src = file.read_text(encoding="utf-8")
        assert 'op.drop_constraint("uix_user_tenant_email"' in src
        assert 'op.create_unique_constraint("uix_user_tenant_email"' in src
        assert '"tenant_id", "email_hash"' in src
