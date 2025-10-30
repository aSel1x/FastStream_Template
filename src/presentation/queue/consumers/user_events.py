from __future__ import annotations

from faststream.annotations import Logger
from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue, RabbitRouter

from presentation.queue.schemas import (
    UserAuthenticatedEventSchema,
    UserCreatedEventSchema,
    UserDeletedEventSchema,
    UserProfileUpdatedEventSchema,
)

user_events_exchange = RabbitExchange(
    name='domain_events',
    type=ExchangeType.TOPIC,
    durable=True,
)


router = RabbitRouter()


@router.subscriber(
    RabbitQueue(
        name='user_created_queue',
        durable=True,
        routing_key='UserCreatedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_created(event: UserCreatedEventSchema, logger: Logger) -> None:
    logger.info(
        'Processing UserCreatedEvent: user_id=%s, username=%s, email=%s',
        event.data.user_id,
        event.data.username,
        event.data.email or 'N/A',
    )


@router.subscriber(
    RabbitQueue(
        name='user_authenticated_queue',
        durable=True,
        routing_key='UserAuthenticatedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_authenticated(
    event: UserAuthenticatedEventSchema, logger: Logger
) -> None:
    logger.info(
        'Processing UserAuthenticatedEvent: user_id=%s, username=%s',
        event.data.user_id,
        event.data.username,
    )


@router.subscriber(
    RabbitQueue(
        name='user_profile_updated_queue',
        durable=True,
        routing_key='UserProfileUpdatedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_profile_updated(
    event: UserProfileUpdatedEventSchema, logger: Logger
) -> None:
    logger.info(
        'Processing UserProfileUpdatedEvent: user_id=%s, updated_fields=%s',
        event.data.user_id,
        event.data.updated_fields,
    )


@router.subscriber(
    RabbitQueue(
        name='user_deleted_queue',
        durable=True,
        routing_key='UserDeletedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_deleted(event: UserDeletedEventSchema, logger: Logger) -> None:
    logger.info('Processing UserDeletedEvent: user_id=%s', event.data.user_id)
