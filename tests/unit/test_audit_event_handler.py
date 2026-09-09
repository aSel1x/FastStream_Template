import inspect
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from domain.audit import event_handler as event_handler_module
from domain.audit.event_handler import AuditEventHandler
from domain.common.event import BaseEvent
from domain.user import events as user_events

# Events that intentionally have no audit entry: they represent a request
# that may never complete (the corresponding *Completed/*Verified event is
# what gets audited), not a state change on their own.
NOT_AUDITED = {'PasswordResetRequestedEvent', 'EmailVerificationRequestedEvent'}


def _all_event_classes() -> list[type[BaseEvent]]:
    return [
        obj
        for _, obj in inspect.getmembers(user_events, inspect.isclass)
        if issubclass(obj, BaseEvent) and obj is not BaseEvent
    ]


class TestEventToActionCompleteness:
    """Every domain event must be either mapped to an audit action or explicitly
    acknowledged as intentionally unaudited — silently dropping one is a bug
    (a real security-relevant mutation, e.g. a permission change, disappears
    from the audit trail with no error anywhere)."""

    def test_every_event_class_is_mapped_or_explicitly_excluded(self):
        unaccounted = [
            cls.__name__
            for cls in _all_event_classes()
            if cls not in event_handler_module.EVENT_TO_ACTION and cls.__name__ not in NOT_AUDITED
        ]
        assert unaccounted == [], f'Event(s) missing from EVENT_TO_ACTION: {unaccounted}'

    def test_every_mapped_event_type_still_exists(self):
        known = set(_all_event_classes())
        stale = [cls.__name__ for cls in event_handler_module.EVENT_TO_ACTION if cls not in known]
        assert stale == [], f'EVENT_TO_ACTION references removed event(s): {stale}'


class TestAuditEventHandler:
    @pytest.mark.asyncio
    async def test_role_updated_event_is_audited(self):
        repo = AsyncMock()
        handler = AuditEventHandler(repo)

        event = user_events.RoleUpdatedEvent(role_id=uuid4(), updated_fields=('permissions',))
        await handler.handle(event)

        repo.add.assert_awaited_once()
        entry = repo.add.await_args.args[0]
        assert entry.entity_type == 'Role'
        assert entry.entity_id == event.role_id

    @pytest.mark.asyncio
    async def test_unmapped_event_is_silently_skipped(self):
        repo = AsyncMock()
        handler = AuditEventHandler(repo)

        await handler.handle(
            user_events.PasswordResetRequestedEvent(
                user_id=uuid4(),
                email='a@b.com',
                reset_token='tok',
            )
        )

        repo.add.assert_not_awaited()
