"""Add region and segment columns to accounts table.

Revision ID: 011
Revises: 010
Create Date: 2026-04-18

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add region column to accounts table
    op.add_column(
        'accounts',
        sa.Column('region', sa.String(100), nullable=True)
    )
    
    # Add segment column to accounts table
    op.add_column(
        'accounts',
        sa.Column('segment', sa.String(100), nullable=True)
    )
    
    # Create index for region column
    op.create_index('ix_accounts_region', 'accounts', ['region'])
    
    # Create index for segment column
    op.create_index('ix_accounts_segment', 'accounts', ['segment'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_accounts_segment', table_name='accounts')
    op.drop_index('ix_accounts_region', table_name='accounts')
    
    # Drop columns
    op.drop_column('accounts', 'segment')
    op.drop_column('accounts', 'region')
