from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable

from domain.common.event import BaseEvent

EventHandler = Callable[[BaseEvent], Awaitable[None]]


class EventBus:
    """Event bus for publishing and subscribing to domain events."""

    def __init__(self) -> None:
        """Initialize event bus with empty handlers."""
        self._handlers: dict[type[BaseEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[BaseEvent],
        handler: EventHandler,
    ) -> None:
        """Subscribe handler to event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async function to handle the event
        """
        self._handlers[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: type[BaseEvent],
        handler: EventHandler,
    ) -> None:
        """Unsubscribe handler from event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    async def publish(self, event: BaseEvent) -> None:
        """Publish event to all registered handlers.

        Args:
            event: Event instance to publish
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        for handler in handlers:
            await handler(event)

    async def publish_many(self, events: list[BaseEvent]) -> None:
        """Publish multiple events in order.

        Args:
            events: List of events to publish
        """
        for event in events:
            await self.publish(event)

    def clear_handlers(self) -> None:
        """Clear all registered handlers."""
        self._handlers.clear()
