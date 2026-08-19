from datetime import datetime
from typing import final
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from domain.common.json_value import JsonValue
from infrastructure.db.sqlalchemy.models.base import BaseModel


@final
class OutboxEvent(BaseModel):
    __tablename__ = 'outbox_events'

    id: Mapped[UUID] = mapped_column(sa.UUID(as_uuid=True), primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    aggregate_id: Mapped[UUID | None] = mapped_column(sa.UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(sa.String, nullable=False)
    payload: Mapped[dict[str, JsonValue]] = mapped_column(sa.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)