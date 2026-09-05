from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from domain.user.value_objects import UserID

if TYPE_CHECKING:
    from domain.user.entities.session import SessionAggregate


class SessionRepositoryInterface(Protocol):
    async def acquire_by_session_id(self, session_id: UUID) -> SessionAggregate | None: ...

    async def acquire_by_user_id(self, user_id: UserID) -> list[SessionAggregate]: ...

    async def acquire_by_token_hash(self, token_hash: bytes) -> SessionAggregate | None: ...

    async def add(self, session: SessionAggregate) -> None: ...

    async def update(self, session: SessionAggregate) -> None: ...

    async def delete(self, session_id: UUID) -> None: ...

    async def delete_by_user_id(self, user_id: UserID) -> None: ...

    async def delete_expired(self, before: datetime) -> int:
        """Remove sessions that expired before `before`. Returns how many were removed."""
        ...
