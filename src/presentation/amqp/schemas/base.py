from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class EventData(BaseModel, Generic[T]):
    """Shape of an outbox event as published to RabbitMQ by ``EventPublisherAMQP.publish_outbox``."""

    event_type: str
    event_id: str
    aggregate_type: str
    aggregate_id: str | None
    created_at: datetime
    payload: T


def event(cls: type[T]) -> type[EventData[T]]:
    """Convert data model to EventSchema class"""
    return EventData[cls]
