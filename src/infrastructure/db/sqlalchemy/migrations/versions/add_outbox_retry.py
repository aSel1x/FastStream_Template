"""Give the outbox retry bookkeeping, secret scrubbing and an index for its poll query.

Revision ID: add_outbox_retry
Revises: add_two_factor_backup_codes
"""

from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'add_outbox_retry'
down_revision: Union[str, None] = 'add_two_factor_backup_codes'
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        'outbox_events',
        sa.Column('sensitive_keys', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'outbox_events',
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column('outbox_events', sa.Column('last_error', sa.Text(), nullable=True))
    op.add_column(
        'outbox_events',
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'outbox_events',
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # jsonb, not json: it is the only one that indexes and compares.
    op.alter_column(
        'outbox_events',
        'payload',
        type_=postgresql.JSONB(astext_type=sa.Text()),
        postgresql_using='payload::jsonb',
    )

    # The worker polls this once a second; without an index it is a seq scan of a table that
    # only ever grows. Partial, so the index stays the size of the backlog rather than the table.
    op.create_index(
        'ix_outbox_events_unprocessed',
        'outbox_events',
        ['next_attempt_at', 'created_at'],
        postgresql_where=sa.text('processed_at IS NULL AND failed_at IS NULL'),
    )
    op.create_index('ix_outbox_events_processed_at', 'outbox_events', ['processed_at'])


def downgrade() -> None:
    op.drop_index('ix_outbox_events_processed_at', table_name='outbox_events')
    op.drop_index('ix_outbox_events_unprocessed', table_name='outbox_events')
    op.alter_column(
        'outbox_events',
        'payload',
        type_=sa.JSON(),
        postgresql_using='payload::json',
    )
    op.drop_column('outbox_events', 'failed_at')
    op.drop_column('outbox_events', 'next_attempt_at')
    op.drop_column('outbox_events', 'last_error')
    op.drop_column('outbox_events', 'attempts')
    op.drop_column('outbox_events', 'sensitive_keys')
