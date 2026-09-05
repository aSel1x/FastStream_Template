"""The unit of work is the only place domain events are collected.

Before this, each use case pulled events off the aggregates it happened to hold. Anything a
service mutated behind the use case's back — every session revoked by a password change, say —
never reached the outbox or the audit log.
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from application.user.services import UserService
from domain.user.entities.session import DeviceInfo, SessionAggregate
from domain.user.entities.user import User
from domain.user.events import (
    PasswordChangedEvent,
    SessionRevokedEvent,
    UserDeletedEvent,
)
from domain.user.value_objects import (
    Email,
    HashedPassword,
    PlainPassword,
    UserID,
    Username,
)
from infrastructure.db.memory.uow import InMemoryUoW


def _user() -> User:
    return User.create(
        user_id=UserID(uuid4()),
        username=Username('testuser'),
        email=Email('test@example.com'),
        hashed_password=HashedPassword(b'hashed'),
        verification_token='token',
    )


def _service(user: User, sessions: list[SessionAggregate], uow: InMemoryUoW) -> UserService:
    user_repo = AsyncMock()
    user_repo.acquire_by_id = AsyncMock(return_value=user)
    user_repo.update = AsyncMock()
    user_repo.check_username_exists = AsyncMock(return_value=False)
    user_repo.check_email_exists = AsyncMock(return_value=False)
    session_repo = AsyncMock()
    session_repo.acquire_by_user_id = AsyncMock(return_value=sessions)
    session_repo.update = AsyncMock()
    crypt = AsyncMock()
    crypt.hash = AsyncMock(return_value=b'new-hash')
    crypt.compare_hashes = AsyncMock(return_value=True)
    return UserService(user_repo, session_repo, crypt, uow)


def _sessions(user_id: UserID, count: int) -> list[SessionAggregate]:
    made = [
        SessionAggregate.create(user_id=user_id, device_info=DeviceInfo()) for _ in range(count)
    ]
    for session in made:
        _ = session.pull_events()  # drop the creation events; only revocation is under test
    return made


class TestEventsSurviveIndirectMutation:
    @pytest.mark.asyncio
    async def test_password_change_emits_a_revocation_event_per_session(self, uow) -> None:
        user = _user()
        _ = user.pull_events()
        sessions = _sessions(user.id, 3)
        service = _service(user, sessions, uow)

        _ = await service.change_password(
            user, PlainPassword('Old@12345'), PlainPassword('New@12345')
        )
        await uow.commit()

        kinds = [type(event) for event in uow.committed_events]
        assert PasswordChangedEvent in kinds
        assert kinds.count(SessionRevokedEvent) == 3, (
            'every session revoked as a side effect must still reach the outbox'
        )

    @pytest.mark.asyncio
    async def test_account_deletion_emits_a_revocation_event_per_session(self, uow) -> None:
        user = _user()
        _ = user.pull_events()
        sessions = _sessions(user.id, 2)
        service = _service(user, sessions, uow)

        _ = await service.delete_user(user.id)
        await uow.commit()

        kinds = [type(event) for event in uow.committed_events]
        assert UserDeletedEvent in kinds
        assert kinds.count(SessionRevokedEvent) == 2

    @pytest.mark.asyncio
    async def test_rollback_discards_pending_events(self, uow) -> None:
        user = _user()
        service = _service(user, [], uow)

        _ = await service.get_user_by_id(user.id)
        _ = await service.update_user(user, username=Username('renamed'))
        await uow.rollback()

        assert uow.committed_events == []
