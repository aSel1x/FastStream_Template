"""Add security, sessions, outbox, rbac tables

Revision ID: add_security_tables
Revises: 65180c3d97a5
Create Date: 2026-04-18 16:00:00

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'add_security_tables'
down_revision: Union[str, None] = '65180c3d97a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Security columns on users
    op.add_column(
        'users', sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column('users', sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('lock_reason', sa.String(), nullable=True))
    op.add_column(
        'users', sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column('users', sa.Column('lock_until', sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        'users',
        sa.Column('is_email_verified', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column('users', sa.Column('email_verification_token', sa.String(), nullable=True))
    op.add_column(
        'users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('email_verification_expires_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column('users', sa.Column('password_reset_token', sa.String(), nullable=True))
    op.add_column(
        'users', sa.Column('password_reset_created_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'users', sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('password_reset_used', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column('users', sa.Column('two_factor_secret', sa.String(), nullable=True))
    op.add_column(
        'users', sa.Column('two_factor_enabled_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Sessions table
    op.create_table(
        'sessions',
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('device_name', sa.String(), nullable=True),
        sa.Column('browser', sa.String(), nullable=True),
        sa.Column('os', sa.String(), nullable=True),
        sa.Column('is_mobile', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('session_id', name=op.f('pk_sessions')),
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])

    # Refresh tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.LargeBinary(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
    )
    op.create_index('ix_refresh_tokens_session_id', 'refresh_tokens', ['session_id'])
    op.create_index('ix_refresh_tokens_token_hash', 'refresh_tokens', ['token_hash'])

    # Outbox events table
    op.create_table(
        'outbox_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('aggregate_type', sa.String(), nullable=False),
        sa.Column('aggregate_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_outbox_events')),
    )

    # RBAC tables
    op.create_table(
        'permissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_permissions')),
        sa.UniqueConstraint('name', name=op.f('uq_permissions_name')),
    )

    op.create_table(
        'roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
        sa.UniqueConstraint('name', name=op.f('uq_roles_name')),
    )

    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('permission_id', sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint('role_id', 'permission_id', name=op.f('pk_role_permissions')),
    )

    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_by', sa.UUID(), nullable=True),
        sa.PrimaryKeyConstraint('user_id', 'role_id', name=op.f('pk_user_roles')),
    )


def downgrade() -> None:
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('outbox_events')
    op.drop_table('refresh_tokens')
    op.drop_index('ix_sessions_user_id', 'sessions')
    op.drop_table('sessions')

    op.drop_column('users', 'two_factor_enabled_at')
    op.drop_column('users', 'two_factor_secret')
    op.drop_column('users', 'password_reset_used')
    op.drop_column('users', 'password_reset_expires_at')
    op.drop_column('users', 'password_reset_created_at')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'email_verification_expires_at')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'is_email_verified')
    op.drop_column('users', 'lock_until')
    op.drop_column('users', 'failed_attempts')
    op.drop_column('users', 'lock_reason')
    op.drop_column('users', 'locked_at')
    op.drop_column('users', 'is_locked')
