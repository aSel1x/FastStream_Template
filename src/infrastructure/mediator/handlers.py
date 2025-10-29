from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeVar

from domain.common.event import BaseEvent
from domain.user.events import (
    UserAuthenticatedEvent,
    UserCreatedEvent,
    UserDeletedEvent,
    UserProfileUpdatedEvent,
)

if TYPE_CHECKING:
    from infrastructure.mediator.event_bus import EventBus

logger = logging.getLogger(__name__)

EventHandlerFunc = Callable[[BaseEvent], Awaitable[None]]
T = TypeVar('T', bound=EventHandlerFunc)

_EVENT_HANDLERS: dict[type[BaseEvent], list[EventHandlerFunc]] = {}


def event_handler(event_type: type[BaseEvent]) -> Callable[[T], T]:
    """Decorator to automatically register event handlers.

    Usage:
        @event_handler(UserCreatedEvent)
        async def handle_user_created(event: BaseEvent) -> None:
            ...

    Args:
        event_type: Type of event this handler processes
    """

    def decorator(func: T) -> T:
        if event_type not in _EVENT_HANDLERS:
            _EVENT_HANDLERS[event_type] = []
        _EVENT_HANDLERS[event_type].append(func)
        return func

    return decorator


@event_handler(UserCreatedEvent)
async def handle_user_created(event: BaseEvent) -> None:
    if not isinstance(event, UserCreatedEvent):
        return

    logger.info(
        f'[EVENT] User created: {event.user_id} ({event.username})',
        extra={
            'event_id': event.event_id,
            'user_id': event.user_id,
            'username': event.username,
            'email': event.email,
        },
    )


@event_handler(UserAuthenticatedEvent)
async def handle_user_authenticated(event: BaseEvent) -> None:
    if not isinstance(event, UserAuthenticatedEvent):
        return

    logger.info(
        f'[EVENT] User authenticated: {event.user_id} ({event.username})',
        extra={
            'event_id': event.event_id,
            'user_id': event.user_id,
            'username': event.username,
        },
    )


@event_handler(UserProfileUpdatedEvent)
async def handle_user_profile_updated(event: BaseEvent) -> None:
    if not isinstance(event, UserProfileUpdatedEvent):
        return

    logger.info(
        f'[EVENT] User profile updated: {event.user_id}, fields: {event.updated_fields}',
        extra={
            'event_id': event.event_id,
            'user_id': event.user_id,
            'updated_fields': event.updated_fields,
        },
    )


@event_handler(UserDeletedEvent)
async def handle_user_deleted(event: BaseEvent) -> None:
    if not isinstance(event, UserDeletedEvent):
        return

    logger.info(
        f'[EVENT] User deleted: {event.user_id}',
        extra={
            'event_id': event.event_id,
            'user_id': event.user_id,
        },
    )


def register_event_handlers(event_bus: EventBus) -> None:
    for event_type, handlers in _EVENT_HANDLERS.items():
        for handler in handlers:
            event_bus.subscribe(event_type, handler)

    logger.info(
        f'Registered {sum(len(h) for h in _EVENT_HANDLERS.values())} event handlers'
    )
