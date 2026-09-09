"""Infrastructure tests that import the SQLAlchemy models."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from domain.common.json_value import JsonValue
from infrastructure.db.sqlalchemy.models.outbox import OutboxEvent

_NO_AGGREGATE = uuid.UUID(int=0)


def _outbox_event(
    *,
    event_type: str = 'UserCreatedEvent',
    aggregate_id: uuid.UUID | None = None,
    payload: dict[str, JsonValue] | None = None,
    sensitive_keys: list[str] | None = None,
) -> OutboxEvent:
    """A real OutboxEvent, not a look-alike.

    The declarative model needs no session to be constructed, and using it means these tests
    break when the row shape changes rather than drifting quietly out of date.
    """
    return OutboxEvent(
        id=uuid.uuid4(),
        aggregate_type='user',
        aggregate_id=uuid.uuid4() if aggregate_id is None else aggregate_id,
        event_type=event_type,
        payload={'user_id': 'u1'} if payload is None else payload,
        sensitive_keys=sensitive_keys,
        created_at=datetime.now(UTC),
        processed_at=None,
        attempts=0,
        last_error=None,
        next_attempt_at=None,
        failed_at=None,
    )


class TestOutboxRepository:
    @pytest.mark.asyncio
    async def test_mark_processed_stamps_and_scrubs_secrets(self) -> None:
        from sqlalchemy.ext.asyncio import AsyncSession

        from infrastructure.db.sqlalchemy.repositories.outbox import OutboxRepository

        repo = OutboxRepository(AsyncMock(spec=AsyncSession))
        event = _outbox_event(
            event_type='PasswordResetRequestedEvent',
            payload={'user_id': 'u1', 'email': 'a@b.c', 'reset_token': 'live-secret'},
            sensitive_keys=['reset_token'],
        )

        await repo.mark_processed([event])

        assert event.processed_at is not None
        assert event.sensitive_keys is None
        assert 'reset_token' not in event.payload, 'a live credential must not outlive delivery'
        assert event.payload['email'] == 'a@b.c'

    @pytest.mark.asyncio
    async def test_reschedule_backs_off_then_dead_letters(self) -> None:
        from sqlalchemy.ext.asyncio import AsyncSession

        from infrastructure.db.sqlalchemy.repositories.outbox import MAX_ATTEMPTS, OutboxRepository

        repo = OutboxRepository(AsyncMock(spec=AsyncSession))
        event = _outbox_event()

        await repo.reschedule(event, 'broker down')

        assert event.attempts == 1
        assert event.failed_at is None
        assert event.next_attempt_at is not None
        assert event.next_attempt_at > datetime.now(UTC)
        assert event.last_error == 'broker down'

        event.attempts = MAX_ATTEMPTS - 1
        await repo.reschedule(event, 'still down')

        assert event.failed_at is not None, 'must dead-letter instead of retrying forever'
        assert event.next_attempt_at is None

    @pytest.mark.asyncio
    async def test_backoff_grows_and_is_capped(self) -> None:
        from infrastructure.db.sqlalchemy.repositories.outbox import (
            BACKOFF_CAP_SECONDS,
            backoff_delay,
        )

        assert backoff_delay(1) < backoff_delay(3) < backoff_delay(5)
        assert backoff_delay(100) == timedelta(seconds=BACKOFF_CAP_SECONDS)


class TestEventPublisherAMQP:
    def _make_publisher(self) -> tuple:
        from infrastructure.queue.config import RabbitMQConfig
        from infrastructure.queue.event_publisher import EventPublisherAMQP

        publisher = EventPublisherAMQP(RabbitMQConfig())
        exchange = AsyncMock()
        publisher._get_exchange = AsyncMock(return_value=exchange)
        return publisher, exchange

    @pytest.mark.asyncio
    async def test_publish_outbox_uses_single_event_format(self) -> None:
        publisher, exchange = self._make_publisher()
        event = _outbox_event()

        failures = await publisher.publish_outbox([event])

        assert failures == []
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
        publisher, exchange = self._make_publisher()
        event = _outbox_event(aggregate_id=_NO_AGGREGATE, payload={})

        await publisher.publish_outbox([event])

        assert exchange.publish.await_args.kwargs['routing_key'] == 'UserCreatedEvent'

    @pytest.mark.asyncio
    async def test_secrets_are_redacted_before_they_reach_the_broker(self) -> None:
        publisher, exchange = self._make_publisher()
        event = _outbox_event(
            event_type='PasswordResetRequestedEvent',
            payload={'user_id': 'u1', 'email': 'a@b.c', 'reset_token': 'live-secret'},
            sensitive_keys=['reset_token'],
        )

        await publisher.publish_outbox([event])

        body = json.loads(exchange.publish.await_args.kwargs['message'].body)
        assert body['payload']['reset_token'] == '[redacted]'
        assert body['payload']['email'] == 'a@b.c'
        assert event.payload['reset_token'] == 'live-secret', 'the stored row is not mutated'

    @pytest.mark.asyncio
    async def test_one_bad_event_does_not_stop_the_batch(self) -> None:
        publisher, exchange = self._make_publisher()
        good_before, bad, good_after = _outbox_event(), _outbox_event(), _outbox_event()
        exchange.publish.side_effect = [None, RuntimeError('unroutable'), None]

        failures = await publisher.publish_outbox([good_before, bad, good_after])

        assert [f.event_id for f in failures] == [bad.id]
        assert exchange.publish.await_count == 3, 'events behind the bad one still go out'
