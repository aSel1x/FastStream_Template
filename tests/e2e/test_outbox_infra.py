"""Infrastructure tests that import the SQLAlchemy models."""
import json
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


def _outbox_event(**overrides: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        'id': uuid.uuid4(),
        'aggregate_type': 'user',
        'aggregate_id': uuid.uuid4(),
        'event_type': 'UserCreatedEvent',
        'payload': {'user_id': 'u1'},
        'created_at': datetime.now(UTC),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_mark_processed_updates_and_commits() -> None:
    from sqlalchemy.sql.dml import Update

    from infrastructure.db.sqlalchemy.repositories.outbox import OutboxRepository
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    repo = OutboxRepository(session)
    ids = [uuid.uuid4(), uuid.uuid4()]

    await repo.mark_processed(ids)

    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()

    statement = session.execute.await_args.args[0]
    assert isinstance(statement, Update)
    assert statement.table.name == 'outbox_events'
    assert statement.whereclause is not None


class TestEventPublisherAMQP:
    def _make_publisher(self) -> tuple:
        from infrastructure.queue.config import RabbitMQConfig
        from infrastructure.queue.event_publisher import EventPublisherAMQP

        publisher = EventPublisherAMQP(RabbitMQConfig())
        channel = AsyncMock()
        exchange = AsyncMock()
        publisher._get_channel = AsyncMock(return_value=channel)
        publisher._get_exchange = AsyncMock(return_value=exchange)
        return publisher, channel, exchange

    @pytest.mark.asyncio
    async def test_publish_outbox_uses_single_event_format(self) -> None:
        publisher, channel, exchange = self._make_publisher()
        event = _outbox_event()

        await publisher.publish_outbox([event])

        exchange.publish.assert_awaited_once()
        message = exchange.publish.await_args.kwargs['message']
        body = json.loads(message.body)

        assert message.content_type == 'application/json'
        assert body['event_type'] == 'UserCreatedEvent'
        assert body['event_id'] == str(event.id)
        assert body['aggregate_type'] == 'user'
        assert body['aggregate_id'] == str(event.aggregate_id)
        assert body['payload'] == {'user_id': 'u1'}
        assert 'created_at' in body

    @pytest.mark.asyncio
    async def test_publish_outbox_routing_key_is_event_type(self) -> None:
        publisher, channel, exchange = self._make_publisher()
        event = _outbox_event(aggregate_id=None, payload={})

        await publisher.publish_outbox([event])

        assert exchange.publish.await_args.kwargs['routing_key'] == 'UserCreatedEvent'

    @pytest.mark.asyncio
    async def test_publish_outbox_closes_channel(self) -> None:
        publisher, channel, exchange = self._make_publisher()
        event = _outbox_event(aggregate_id=None, payload={})

        await publisher.publish_outbox([event])

        channel.close.assert_awaited_once()
