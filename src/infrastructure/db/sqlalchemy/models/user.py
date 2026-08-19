from uuid import UUID

from infrastructure.db.sqlalchemy.models.base import create_table

import sqlalchemy as sa

USER_ID_COLUMN: sa.Column[UUID] = sa.Column('id', sa.UUID(as_uuid=True), primary_key=True)

USERS_TABLE = create_table(
    'users',
    USER_ID_COLUMN,
    sa.Column('username', sa.String, unique=True, nullable=False),
    sa.Column('email', sa.String, unique=True, nullable=True),
    sa.Column('hashed_password', sa.LargeBinary, nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_locked', sa.Boolean, default=False, nullable=False),
    sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lock_reason', sa.String, nullable=True),
    sa.Column('failed_attempts', sa.Integer, default=0, nullable=False),
    sa.Column('lock_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_email_verified', sa.Boolean, default=False, nullable=False),
    sa.Column('email_verification_token', sa.String, nullable=True),
    sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('email_verification_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('password_reset_token', sa.String, nullable=True),
    sa.Column('password_reset_created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('password_reset_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('password_reset_used', sa.Boolean, default=False, nullable=False),
    sa.Column('two_factor_secret', sa.String, nullable=True),
    sa.Column('two_factor_enabled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('two_factor_backup_codes', sa.JSON, nullable=True),
)
