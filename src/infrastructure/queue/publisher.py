from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import aio_pika
from aio_pika.pool import Pool

if TYPE_CHECKING:
    from aio_pika.abc import AbstractChannel, AbstractConnection
    from domain.common.event import BaseEvent

    from infrastructure.queue.config import RabbitMQConfig

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes domain events to RabbitMQ using aio-pika."""

    _config: RabbitMQConfig
    _connection_pool: Pool[AbstractConnection] | None
    _channel_pool: Pool[AbstractChannel] | None

    def __init__(self, config: RabbitMQConfig) -> None:
        self._config = config
        self._connection_pool = None
        self._channel_pool = None

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

    async def publish(self, event: BaseEvent) -> None:
        await self.publish_many([event])

    async def publish_many(self, events: list[BaseEvent]) -> None:
        if not events:
            return

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
            logger.warning('Failed to publish events batch: %s', str(e))
        finally:
            if channel is not None:
                await channel.close()
