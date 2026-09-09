import sqlalchemy as sa
from infrastructure.db.sqlalchemy.models.base import create_table

SESSIONS_TABLE = create_table(
    'sessions',
    sa.Column('session_id', sa.UUID(as_uuid=True), primary_key=True),
    sa.Column('user_id', sa.UUID(as_uuid=True), nullable=False, index=True),
    sa.Column('user_agent', sa.String, nullable=True),
    sa.Column('ip_address', sa.String, nullable=True),
    sa.Column('device_name', sa.String, nullable=True),
    sa.Column('browser', sa.String, nullable=True),
    sa.Column('os', sa.String, nullable=True),
    sa.Column('is_mobile', sa.Boolean, default=False, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column('is_revoked', sa.Boolean, default=False, nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
)

REFRESH_TOKENS_TABLE = create_table(
    'refresh_tokens',
    sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
    sa.Column('session_id', sa.UUID(as_uuid=True), nullable=False, index=True),
    sa.Column('token_hash', sa.LargeBinary, nullable=False, unique=True, index=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('is_revoked', sa.Boolean, default=False, nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'], ondelete='CASCADE'),
)
