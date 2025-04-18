"""add is_admin and is_active columns to users table

Revision ID: add_admin_active_columns
Revises: b7e89c1d2f3a
Create Date: 2025-04-18 14:36:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'add_admin_active_columns'
down_revision: Union[str, None] = 'b7e89c1d2f3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # is_adminカラムの追加
    op.add_column('users',
        sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false')
    )
    # is_activeカラムの追加
    op.add_column('users',
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true')
    )


def downgrade() -> None:
    # カラムの削除
    op.drop_column('users', 'is_active')
    op.drop_column('users', 'is_admin')
