"""Add missing two_factor_backup_codes column

users.two_factor_secret / two_factor_enabled_at were added by add_security_tables,
but the ORM model (USERS_TABLE) and the domain VO both track backup codes too, and
there was never a column for them — they were silently unpersisted.

Revision ID: add_two_factor_backup_codes
Revises: drop_oauth_and_keys_tables
Create Date: 2026-08-19 13:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_two_factor_backup_codes'
down_revision: Union[str, None] = 'drop_oauth_and_keys_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('two_factor_backup_codes', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'two_factor_backup_codes')
