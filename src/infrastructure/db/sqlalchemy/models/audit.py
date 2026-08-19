import sqlalchemy as sa
from infrastructure.db.sqlalchemy.models.base import create_table

AUDIT_LOGS_TABLE = create_table(
    'audit_logs',
    sa.Column('id', sa.UUID(as_uuid=True), primary_key=True),
    sa.Column('user_id', sa.UUID(as_uuid=True), nullable=True, index=True),
    sa.Column('action', sa.String, nullable=False, index=True),
    sa.Column('entity_type', sa.String, nullable=False),
    sa.Column('entity_id', sa.UUID(as_uuid=True), nullable=True),
    sa.Column('details', sa.JSON, nullable=False),
    sa.Column('ip_address', sa.String, nullable=True),
    sa.Column('user_agent', sa.String, nullable=True),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column('success', sa.Boolean, nullable=False, server_default='true'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
)