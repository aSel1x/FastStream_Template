import json
import logging
from collections.abc import Iterable
from typing import override

import aio_pika
from aio_pika.abc import AbstractChannel, AbstractConnection
from application.common.interfaces.event_bus import EventPublisherInterface
from domain.common.event import BaseEvent

from infrastructure.queue.config import RabbitMQConfig

logger = logging.getLogger(__name__)


class EventPublisherAMQP(EventPublisherInterface):
    """Event publisher for publishing domain events to RabbitMQ."""

    _config: RabbitMQConfig

    def __init__(self, config: RabbitMQConfig) -> None:
        """Initialize event publisher with RabbitMQ configuration."""
        self._config = config

    async def _get_connection(self) -> AbstractConnection:
        return await aio_pika.connect_robust(self._config.url)

    async def _get_channel(self) -> AbstractChannel:
        connection = await self._get_connection()
        return await connection.channel()

    @staticmethod
    def _serialize_value(value: object) -> str | int | float | bool | None:
        if isinstance(value, str):
            return value
        if isinstance(value, int | float | bool):
            return value
        if value is None:
            return None
        return str(value)

    @override
    async def publish(self, events: Iterable[BaseEvent]) -> None:
        """Publish event to RabbitMQ."""
        channel: AbstractChannel | None = None
        try:
            channel = await self._get_channel()
            exchange = await channel.declare_exchange(
                name='domain_events',
                type=aio_pika.ExchangeType.TOPIC,
                durable=True,
            )

            for event in events:
                routing_key = event.__class__.__name__

                event_dict: dict[str, object] = event.__dict__
                event_data = {
                    'event_type': event.__class__.__name__,
                    'event_id': str(event.event_id),
                    'event_timestamp': event.event_timestamp,
                    'data': {
                        k: self._serialize_value(v)
                        for k, v in event_dict.items()
                        if not k.startswith('event_')
                    },
                }
                message_body = json.dumps(event_data)

                _ = await exchange.publish(
                    message=aio_pika.Message(
                        body=message_body.encode(),
                        content_type='application/json',
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    ),
                    routing_key=routing_key,
                )
        except Exception as e:
            logger.warning('Failed to publish event to RabbitMQ: %s', str(e))
        finally:
            if channel is not None:
                await channel.close()
