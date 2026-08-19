import logging
from collections.abc import Iterable

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange
from pydantic import JsonValue, TypeAdapter

from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent
from infrastructure.queue.config import RabbitMQConfig

_event_data_adapter = TypeAdapter[dict[str, JsonValue]](dict[str, JsonValue])

logger = logging.getLogger(__name__)


class EventPublisherAMQP:
    """Publishes transactional-outbox events to RabbitMQ."""

    _config: RabbitMQConfig

    def __init__(self, config: RabbitMQConfig) -> None:
        """Initialize event publisher with RabbitMQ configuration."""
        self._config = config

    async def _get_connection(self) -> AbstractConnection:
        return await aio_pika.connect_robust(self._config.url)

    async def _get_channel(self) -> AbstractChannel:
        connection = await self._get_connection()
        return await connection.channel()

    async def _get_exchange(self, channel: AbstractChannel) -> AbstractExchange:
        return await channel.declare_exchange(
            name='domain_events',
            type=aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

    async def _publish(
        self,
        exchange: AbstractExchange,
        routing_key: str,
        body: bytes,
    ) -> None:
        _ = await exchange.publish(
            message=aio_pika.Message(
                body=body,
                content_type='application/json',
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )

    async def publish_outbox(self, events: Iterable[OutboxEvent]) -> None:
        """Publish outbox events to RabbitMQ using the single message format."""
        channel: AbstractChannel | None = None
        try:
            channel = await self._get_channel()
            exchange = await self._get_exchange(channel)

            for event in events:
                event_data: dict[str, JsonValue] = {
                    'event_type': event.event_type,
                    'event_id': str(event.id),
                    'aggregate_type': event.aggregate_type,
                    'aggregate_id': str(event.aggregate_id) if event.aggregate_id else None,
                    'payload': event.payload,
                    'created_at': event.created_at.isoformat(),
                }
                await self._publish(exchange, event.event_type, _event_data_adapter.dump_json(event_data))
        except Exception as e:
            logger.error('Failed to publish outbox events to RabbitMQ: %s', str(e))
            raise
        finally:
            if channel is not None:
                await channel.close()
