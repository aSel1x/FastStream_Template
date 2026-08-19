from typing import final
from uuid import UUID

from application.common.interfaces import HydraAdminClientInterface, UnitOfWorkInterface
from application.user.services import UserService
from domain.user.value_objects import UserID


@final
class RevokeSessionUseCase:
    def __init__(
        self,
        user_service: UserService,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._uow = uow

    async def __call__(self, user_id: UUID, session_id: str) -> None:
        session = await self._user_service.revoke_session(UUID(session_id), UserID(user_id))
        if session:
            self._uow.add_events(session.pull_events())
            await self._uow.commit()


@final
class RevokeAllSessionsUseCase:
    def __init__(
        self,
        user_service: UserService,
        hydra: HydraAdminClientInterface,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._hydra = hydra
        self._uow = uow

    async def __call__(self, user_id: UUID) -> None:
        sessions = await self._user_service.revoke_all_sessions(UserID(user_id))
        for session in sessions:
            self._uow.add_events(session.pull_events())
        await self._uow.commit()

        # Revoking our own sessions only stops future refresh-token renewal — the OAuth2
        # access/refresh tokens Hydra already issued to this subject stay valid until they
        # expire unless we also kill the Hydra-side consent/login sessions here.
        subject = str(user_id)
        await self._hydra.revoke_consent_sessions(subject)
        await self._hydra.revoke_login_sessions(subject)
