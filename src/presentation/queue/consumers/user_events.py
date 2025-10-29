from __future__ import annotations

import logging

from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue, RabbitRouter

from presentation.queue.schemas import (
    UserAuthenticatedEventSchema,
    UserCreatedEventSchema,
    UserDeletedEventSchema,
    UserProfileUpdatedEventSchema,
)

logger = logging.getLogger(__name__)


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
async def handle_user_created(event: UserCreatedEventSchema) -> None:
    user_id = event.data.user_id
    username = event.data.username
    email = event.data.email or 'N/A'

    logger.info(
        'Processing UserCreatedEvent: user_id=%s, username=%s, email=%s',
        user_id,
        username,
        email,
    )

    logger.info('Sending welcome email to %s (%s)', username, email)

    logger.info('Initializing analytics for user %s', user_id)

    logger.info('Successfully processed UserCreatedEvent for user %s', user_id)


@router.subscriber(
    RabbitQueue(
        name='user_authenticated_queue',
        durable=True,
        routing_key='UserAuthenticatedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_authenticated(event: UserAuthenticatedEventSchema) -> None:
    user_id = event.data.user_id
    username = event.data.username

    logger.info(
        'Processing UserAuthenticatedEvent: user_id=%s, username=%s',
        user_id,
        username,
    )

    logger.info('Updating last login timestamp for user %s', user_id)

    logger.info('Recording authentication analytics for user %s', user_id)

    logger.info('Successfully processed UserAuthenticatedEvent for user %s', user_id)


@router.subscriber(
    RabbitQueue(
        name='user_profile_updated_queue',
        durable=True,
        routing_key='UserProfileUpdatedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_profile_updated(event: UserProfileUpdatedEventSchema) -> None:
    user_id = event.data.user_id
    updated_fields = event.data.updated_fields

    logger.info(
        'Processing UserProfileUpdatedEvent: user_id=%s, updated_fields=%s',
        user_id,
        updated_fields,
    )

    logger.info('Syncing user profile %s with external systems', user_id)

    logger.info('Invalidating cache for user %s', user_id)

    logger.info('Successfully processed UserProfileUpdatedEvent for user %s', user_id)


@router.subscriber(
    RabbitQueue(
        name='user_deleted_queue',
        durable=True,
        routing_key='UserDeletedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_deleted(event: UserDeletedEventSchema) -> None:
    user_id = event.data.user_id

    logger.info('Processing UserDeletedEvent: user_id=%s', user_id)

    logger.info('Cleaning up data for deleted user %s', user_id)

    logger.info('Removing analytics data for user %s', user_id)

    logger.info('Successfully processed UserDeletedEvent for user %s', user_id)
