import logging
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractRobustConnection
from pydantic import JsonValue, TypeAdapter

from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent
from infrastructure.queue.config import RabbitMQConfig

_event_data_adapter = TypeAdapter[dict[str, JsonValue]](dict[str, JsonValue])

logger = logging.getLogger(__name__)

EXCHANGE_NAME = 'domain_events'
REDACTED = '[redacted]'


@dataclass(frozen=True, slots=True)
class PublishFailure:
    """An event that could not be published, and why."""

    event_id: UUID
    error: str


class EventPublisherAMQP:
    """Publishes transactional-outbox events to RabbitMQ.

    Holds a single robust connection for its lifetime. `connect_robust` reconnects on its own
    and keeps itself alive, so opening one per batch leaks a connection on every poll and adds
    a full handshake to every publish.
    """

    def __init__(self, config: RabbitMQConfig) -> None:
        self._config: RabbitMQConfig = config
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None

    async def _get_exchange(self) -> AbstractExchange:
        channel_usable = self._channel is not None and not self._channel.is_closed
        if self._exchange is not None and channel_usable:
            return self._exchange

        if self._connection is None or self._connection.is_closed:
            self._connection = await aio_pika.connect_robust(self._config.url)

        self._channel = await self._connection.channel()
        self._exchange = await self._channel.declare_exchange(
            name=EXCHANGE_NAME,
            type=aio_pika.ExchangeType.TOPIC,
            durable=True,
        )
        return self._exchange

    async def close(self) -> None:
        """Release the channel and connection. Call once, on shutdown."""
        if self._channel is not None and not self._channel.is_closed:
            await self._channel.close()
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
        self._channel = None
        self._connection = None
        self._exchange = None

    async def publish_event(self, event: OutboxEvent) -> None:
        """Publish one outbox event. Raises if the broker rejects it."""
        exchange = await self._get_exchange()
        _ = await exchange.publish(
            message=aio_pika.Message(
                body=_event_data_adapter.dump_json(wire_payload(event)),
                content_type='application/json',
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                message_id=str(event.id),
            ),
            routing_key=event.event_type,
        )

    async def publish_outbox(self, events: Iterable[OutboxEvent]) -> list[PublishFailure]:
        """Publish each event independently, returning the ones that failed.

        Isolating failures per event is what keeps a single unpublishable payload from
        blocking every event queued behind it.
        """
        failures: list[PublishFailure] = []
        for event in events:
            try:
                await self.publish_event(event)
            except Exception as exc:
                logger.warning('Failed to publish outbox event %s: %s', event.id, exc)
                failures.append(PublishFailure(event_id=event.id, error=repr(exc)))
        return failures


def wire_payload(event: OutboxEvent) -> dict[str, JsonValue]:
    """The published message body, with any secret-carrying field redacted.

    Reset tokens, verification tokens and 2FA backup codes are needed by the outbox worker to
    render an email, but must never reach the topic exchange: anything bound to it would
    otherwise receive live credentials.
    """
    payload: dict[str, JsonValue] = dict(event.payload)
    for key in event.sensitive_keys or ():
        if key in payload:
            payload[key] = REDACTED

    return {
        'event_type': event.event_type,
        'event_id': str(event.id),
        'aggregate_type': event.aggregate_type,
        'aggregate_id': str(event.aggregate_id) if event.aggregate_id else None,
        'payload': payload,
        'created_at': event.created_at.isoformat(),
    }
