from datetime import datetime
from typing import final
from uuid import UUID

import sqlalchemy as sa
from domain.common.json_value import JsonValue
from infrastructure.db.sqlalchemy.models.base import BaseModel
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


@final
class OutboxEvent(BaseModel):
    __tablename__ = 'outbox_events'
    id: Mapped[UUID] = mapped_column(sa.UUID(as_uuid=True), primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    aggregate_id: Mapped[UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    payload: Mapped[dict[str, JsonValue]] = mapped_column(JSONB, nullable=False)
    # Payload keys that carry a live credential: never published to the broker, and scrubbed
    # from the row once the event has been handled.
    sensitive_keys: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # Retry bookkeeping. Without it one unpublishable event blocks the queue head forever.
    attempts: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default='0')
    last_error: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    failed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)


# Declared outside the class: SQLAlchemy types `__table_args__` loosely, and the rest of this
# schema is Core-style anyway.

# The worker polls `WHERE processed_at IS NULL ORDER BY created_at` once a second. Partial, so
# the index stays the size of the backlog rather than of the whole table.
OUTBOX_UNPROCESSED_INDEX = sa.Index(
    'ix_outbox_events_unprocessed',
    OutboxEvent.next_attempt_at,
    OutboxEvent.created_at,
    postgresql_where=sa.text('processed_at IS NULL AND failed_at IS NULL'),
)

# Supports the retention sweep.
OUTBOX_PROCESSED_AT_INDEX = sa.Index('ix_outbox_events_processed_at', OutboxEvent.processed_at)
