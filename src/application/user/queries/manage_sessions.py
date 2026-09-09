from dataclasses import dataclass
from typing import final
from uuid import UUID

from domain.user.interfaces.persistence.readers import SessionReadDTO, SessionReader
from domain.user.value_objects import UserID


@dataclass
class PaginationParams:
    limit: int = 20
    offset: int = 0


@dataclass
class SessionsPage:
    sessions: list[SessionReadDTO]
    total: int
    limit: int
    offset: int
    has_more: bool


@final
class GetUserSessionsUseCase:
    def __init__(self, session_reader: SessionReader) -> None:
        self._session_reader = session_reader

    async def __call__(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> SessionsPage:
        all_sessions = await self._session_reader.get_by_user_id(UserID(user_id))
        total = len(all_sessions)

        paginated = all_sessions[offset : offset + limit]

        return SessionsPage(
            sessions=paginated,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )
