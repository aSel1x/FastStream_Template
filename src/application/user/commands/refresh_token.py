from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.interfaces import UnitOfWorkInterface
from application.user.services import UserService


@dataclass
class RefreshTokenInput:
    refresh_token: str


@dataclass
class RefreshTokenOutput:
    user_id: UUID
    session_id: str
    expires_at: str


@final
class RefreshTokenUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow

    async def __call__(self, input: RefreshTokenInput) -> RefreshTokenOutput:
        session, user = await self._user_service.refresh_session(input.refresh_token)

        self._uow.add_events(user.pull_events())
        self._uow.add_events(session.pull_events())
        await self._uow.commit()

        return RefreshTokenOutput(
            user_id=user.id.to_raw(),
            session_id=str(session.session_id),
            expires_at=session.expires_at.isoformat(),
        )
