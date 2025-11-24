from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class EventData(BaseModel, Generic[T]):
    event_type: str
    event_id: str
    event_timestamp: int
    data: T


def event(cls: type[T]) -> type[EventData[T]]:
    """Convert data model to EventSchema class"""
    return EventData[cls]
