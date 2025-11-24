from collections.abc import Iterable
from typing import Protocol

from domain.common.event import BaseEvent


class EventPublisherInterface(Protocol):
    """Interface for event publisher to publish domain events."""

    async def publish(self, events: Iterable[BaseEvent]) -> None:
        """Publish multiple events in order."""
        raise NotImplementedError
