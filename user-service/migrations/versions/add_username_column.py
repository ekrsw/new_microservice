"""add username column and modify fullname column

Revision ID: add_username_column
Revises: add_admin_active_columns
Create Date: 2025-04-18 15:13:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'add_username_column'
down_revision: Union[str, None] = 'add_admin_active_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # usernameカラムの追加
    op.add_column('users',
        sa.Column('username', sa.String(), nullable=True)
    )
    
    # 既存のデータに対して、fullnameの値をusernameにコピー
    op.execute("UPDATE users SET username = fullname")
    
    # usernameカラムにNOT NULL制約を追加
    op.alter_column('users', 'username', nullable=False)
    
    # usernameカラムに一意インデックスを作成
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # fullnameカラムの一意インデックスを削除
    op.drop_index(op.f('ix_users_fullname'), table_name='users')
    
    # fullnameカラムのインデックスを再作成（一意制約なし）
    op.create_index(op.f('ix_users_fullname'), 'users', ['fullname'], unique=False)
    
    # fullnameカラムのNULL制約を削除
    op.alter_column('users', 'fullname', nullable=True)


def downgrade() -> None:
    # fullnameカラムにNOT NULL制約を再追加
    op.execute("UPDATE users SET fullname = username WHERE fullname IS NULL")
    op.alter_column('users', 'fullname', nullable=False)
    
    # fullnameカラムのインデックスを削除して一意インデックスを再作成
    op.drop_index(op.f('ix_users_fullname'), table_name='users')
    op.create_index(op.f('ix_users_fullname'), 'users', ['fullname'], unique=True)
    
    # usernameカラムのインデックスを削除
    op.drop_index(op.f('ix_users_username'), table_name='users')
    
    # usernameカラムを削除
    op.drop_column('users', 'username')
