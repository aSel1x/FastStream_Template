"""Add foreign key constraints

Revision ID: add_foreign_keys
Revises: add_oauth_tables
Create Date: 2026-04-18 19:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'add_foreign_keys'
down_revision: Union[str, None] = 'add_oauth_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('authorization_codes', sa.Column('session_id', sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        op.f('fk_sessions_user_id_users'),
        'sessions', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_refresh_tokens_session_id_sessions'),
        'refresh_tokens', 'sessions',
        ['session_id'], ['session_id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_role_permissions_role_id_roles'),
        'role_permissions', 'roles',
        ['role_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_role_permissions_permission_id_permissions'),
        'role_permissions', 'permissions',
        ['permission_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_user_roles_user_id_users'),
        'user_roles', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_user_roles_role_id_roles'),
        'user_roles', 'roles',
        ['role_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_user_roles_assigned_by_users'),
        'user_roles', 'users',
        ['assigned_by'], ['id'],
        ondelete='SET NULL',
    )
    op.create_foreign_key(
        op.f('fk_authorization_codes_client_id_oauth_clients'),
        'authorization_codes', 'oauth_clients',
        ['client_id'], ['client_id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_authorization_codes_user_id_users'),
        'authorization_codes', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_foreign_key(
        op.f('fk_audit_logs_user_id_users'),
        'audit_logs', 'users',
        ['user_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_audit_logs_user_id_users'), 'audit_logs', type_='foreignkey')
    op.drop_constraint(op.f('fk_authorization_codes_user_id_users'), 'authorization_codes', type_='foreignkey')
    op.drop_constraint(op.f('fk_authorization_codes_client_id_oauth_clients'), 'authorization_codes', type_='foreignkey')
    op.drop_constraint(op.f('fk_user_roles_assigned_by_users'), 'user_roles', type_='foreignkey')
    op.drop_constraint(op.f('fk_user_roles_role_id_roles'), 'user_roles', type_='foreignkey')
    op.drop_constraint(op.f('fk_user_roles_user_id_users'), 'user_roles', type_='foreignkey')
    op.drop_constraint(op.f('fk_role_permissions_permission_id_permissions'), 'role_permissions', type_='foreignkey')
    op.drop_constraint(op.f('fk_role_permissions_role_id_roles'), 'role_permissions', type_='foreignkey')
    op.drop_constraint(op.f('fk_refresh_tokens_session_id_sessions'), 'refresh_tokens', type_='foreignkey')
    op.drop_constraint(op.f('fk_sessions_user_id_users'), 'sessions', type_='foreignkey')
    op.drop_column('authorization_codes', 'session_id')
