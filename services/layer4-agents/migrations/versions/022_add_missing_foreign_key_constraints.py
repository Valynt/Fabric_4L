"""Retire invalid Layer 4 foreign-key assumptions.

Revision ID: 022
Revises: 021
Create Date: 2026-05-03

The original revision targeted an unprefixed usage-events table that is not part
of the Layer 4 schema and attempted to link the string-valued integrations
tenant identifier to the UUID tenant registry. Neither operation represents a
valid Layer 4 constraint, so this pre-production revision intentionally makes no
schema change.
"""

from collections.abc import Sequence
from typing import Union

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Preserve the revision chain without applying invalid constraints."""


def downgrade() -> None:
    """No schema changes were applied by this revision."""
