from faststream.annotations import Logger
from faststream.rabbit import ExchangeType, RabbitExchange, RabbitQueue, RabbitRouter

from presentation.amqp.schemas.user import (
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

#: Where a message goes after it has failed too many times. Without one, a message the
#: consumer cannot handle is redelivered forever and blocks everything behind it.
dead_letter_exchange = RabbitExchange(
    name='domain_events.dlx',
    type=ExchangeType.TOPIC,
    durable=True,
)

MAX_DELIVERIES = 5

#: Applied to every queue below. `x-death` counts redeliveries; past the limit the broker
#: routes the message to the dead-letter exchange instead of back to the queue.
QUEUE_ARGUMENTS: dict[str, object] = {
    'x-dead-letter-exchange': dead_letter_exchange.name,
    'x-delivery-limit': MAX_DELIVERIES,
    'x-queue-type': 'quorum',
}


router = RabbitRouter()


@router.subscriber(
    RabbitQueue(
        name='user_created_queue',
        durable=True,
        arguments=QUEUE_ARGUMENTS,
        routing_key='UserCreatedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_created(event: UserCreatedEventSchema, logger: Logger) -> None:
    logger.info(
        'Processing UserCreatedEvent: user_id=%s, username=%s, email=%s',
        event.payload.user_id,
        event.payload.username,
        event.payload.email or 'N/A',
    )


@router.subscriber(
    RabbitQueue(
        name='user_authenticated_queue',
        durable=True,
        arguments=QUEUE_ARGUMENTS,
        routing_key='UserAuthenticatedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_authenticated(event: UserAuthenticatedEventSchema, logger: Logger) -> None:
    logger.info(
        'Processing UserAuthenticatedEvent: user_id=%s, username=%s',
        event.payload.user_id,
        event.payload.username,
    )


@router.subscriber(
    RabbitQueue(
        name='user_profile_updated_queue',
        durable=True,
        arguments=QUEUE_ARGUMENTS,
        routing_key='UserProfileUpdatedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_profile_updated(event: UserProfileUpdatedEventSchema, logger: Logger) -> None:
    logger.info(
        'Processing UserProfileUpdatedEvent: user_id=%s, updated_fields=%s',
        event.payload.user_id,
        event.payload.updated_fields,
    )


@router.subscriber(
    RabbitQueue(
        name='user_deleted_queue',
        durable=True,
        arguments=QUEUE_ARGUMENTS,
        routing_key='UserDeletedEvent',
    ),
    exchange=user_events_exchange,
)
async def handle_user_deleted(event: UserDeletedEventSchema, logger: Logger) -> None:
    logger.info('Processing UserDeletedEvent: user_id=%s', event.payload.user_id)
