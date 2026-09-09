from dataclasses import dataclass
from typing import final
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
    #: A new token every time. The one that was presented is now revoked.
    refresh_token: str


@final
class RefreshTokenUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow

    async def __call__(self, data: RefreshTokenInput) -> RefreshTokenOutput:
        session, user, refresh_token = await self._user_service.refresh_session(data.refresh_token)
        await self._uow.commit()

        return RefreshTokenOutput(
            user_id=user.id.to_raw(),
            session_id=str(session.session_id),
            expires_at=session.expires_at.isoformat(),
            refresh_token=refresh_token,
        )
