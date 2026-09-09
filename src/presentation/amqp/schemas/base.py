from datetime import datetime

from pydantic import BaseModel


class EventData[T: BaseModel](BaseModel):
    """Shape of an outbox event as published to RabbitMQ by the outbox publisher."""

    event_type: str
    event_id: str
    aggregate_type: str
    aggregate_id: str | None
    created_at: datetime
    payload: T


def event[T: BaseModel](cls: type[T]) -> type[EventData[T]]:
    """Convert data model to EventSchema class"""
    return EventData[cls]
