"""Optimistic locking for users, plus the indexes the hot queries were missing.

`users.version` makes every update conditional, so two concurrent requests can no longer both
spend the same 2FA backup code or lose a failed-login increment.

The indexes cover foreign-key columns that are not the leading column of their primary key
(Postgres does not index those automatically) and the audit-log lookup by entity.

Revision ID: add_user_version_and_indexes
Revises: hash_and_encrypt_user_secrets
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'add_user_version_and_indexes'
down_revision: Union[str, None] = 'hash_and_encrypt_user_secrets'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('version', sa.Integer(), nullable=False, server_default='0'),
    )

    # Non-leading FK columns: a delete on the parent otherwise scans the whole child table.
    op.create_index('ix_user_roles_role_id', 'user_roles', ['role_id'])
    op.create_index('ix_user_roles_assigned_by', 'user_roles', ['assigned_by'])
    op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'])

    # audit_logs.get_by_entity had no supporting index at all.
    op.create_index('ix_audit_logs_entity', 'audit_logs', ['entity_type', 'entity_id'])

    # Sessions are swept by expiry; without this the janitor scans every row.
    op.create_index('ix_sessions_expires_at', 'sessions', ['expires_at'])

    # A refresh token hash must identify at most one token.
    op.drop_index('ix_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.create_index(
        'ix_refresh_tokens_token_hash',
        'refresh_tokens',
        ['token_hash'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_refresh_tokens_token_hash', table_name='refresh_tokens')
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])
    op.drop_index('ix_sessions_expires_at', table_name='sessions')
    op.drop_index('ix_audit_logs_entity', table_name='audit_logs')
    op.drop_index('ix_role_permissions_permission_id', table_name='role_permissions')
    op.drop_index('ix_user_roles_assigned_by', table_name='user_roles')
    op.drop_index('ix_user_roles_role_id', table_name='user_roles')
    op.drop_column('users', 'version')
