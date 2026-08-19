from uuid import UUID

import sqlalchemy as sa
from infrastructure.db.sqlalchemy.models.base import create_table

PERMISSION_ID_COLUMN: sa.Column[UUID] = sa.Column('id', sa.UUID(as_uuid=True), primary_key=True)
PERMISSION_NAME_COLUMN: sa.Column[str] = sa.Column('name', sa.String, unique=True, nullable=False)

PERMISSIONS_TABLE = create_table(
    'permissions',
    PERMISSION_ID_COLUMN,
    PERMISSION_NAME_COLUMN,
    sa.Column('description', sa.String, nullable=True),
)

ROLES_TABLE = create_table(
    'roles',
    sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
    sa.Column('name', sa.String, unique=True, nullable=False),
    sa.Column('description', sa.String, nullable=True),
)

ROLE_PERMISSIONS_TABLE = create_table(
    'role_permissions',
    sa.Column('role_id', sa.UUID(as_uuid=True), nullable=False),
    sa.Column('permission_id', sa.UUID(as_uuid=True), nullable=False),
    sa.PrimaryKeyConstraint('role_id', 'permission_id'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
)

USER_ROLES_TABLE = create_table(
    'user_roles',
    sa.Column('user_id', sa.UUID(as_uuid=True), nullable=False),
    sa.Column('role_id', sa.UUID(as_uuid=True), nullable=False),
    sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('assigned_by', sa.UUID(as_uuid=True), nullable=True),
    sa.PrimaryKeyConstraint('user_id', 'role_id'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ondelete='SET NULL'),
)
