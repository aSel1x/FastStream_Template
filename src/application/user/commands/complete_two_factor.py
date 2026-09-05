from dataclasses import dataclass
from typing import final
from uuid import UUID

from application.common.interfaces import UnitOfWorkInterface
from application.user.replay_guard import UsedCodeRegistry
from application.user.services import UserService
from application.user.two_factor_challenge import (
    TwoFactorChallengeExpiredError,
    TwoFactorChallengeStore,
)
from domain.user.interfaces import TwoFactorInterface, UserRepositoryInterface
from domain.user.value_objects import UserID


@dataclass
class CompleteTwoFactorInput:
    challenge_token: str
    code: str


@dataclass
class CompleteTwoFactorOutput:
    user_id: UUID
    session_id: str
    refresh_token: str
    #: Only set when the challenge came from the Hydra login bridge.
    login_challenge: str | None = None


@final
class CompleteTwoFactorUseCase:
    """Turns a verified second factor into a session.

    This is the only place a session is created for an account with 2FA enabled — which is
    what makes the second factor mandatory rather than advisory.
    """

    def __init__(
        self,
        user_service: UserService,
        user_repo: UserRepositoryInterface,
        two_factor: TwoFactorInterface,
        challenges: TwoFactorChallengeStore,
        used_codes: UsedCodeRegistry,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._user_repo = user_repo
        self._two_factor = two_factor
        self._challenges = challenges
        self._used_codes = used_codes
        self._uow = uow

    async def __call__(self, data: CompleteTwoFactorInput) -> CompleteTwoFactorOutput:
        challenge = await self._challenges.read(data.challenge_token)

        user = await self._user_repo.acquire_by_id(UserID(challenge.user_id))
        if user is None or user.is_deleted() or user.is_locked():
            await self._challenges.discard(data.challenge_token)
            raise TwoFactorChallengeExpiredError()

        # A TOTP code stays valid for its whole window, and verifying does not consume it.
        if await self._used_codes.was_used(challenge.user_id, data.code):
            await self._challenges.record_failure(data.challenge_token, challenge)
            raise TwoFactorChallengeExpiredError()

        verified, updated_user = user.verify_two_factor(data.code, self._two_factor)
        if not verified:
            await self._challenges.record_failure(data.challenge_token, challenge)
            raise TwoFactorChallengeExpiredError()

        # A consumed backup code (or a spent TOTP code) has to be persisted before the
        # session exists, so it cannot be replayed against a second challenge.
        if updated_user is not user:
            await self._user_repo.update(updated_user)
            self._uow.register(updated_user)

        await self._used_codes.remember(challenge.user_id, data.code)

        # One-shot: the challenge is gone whether or not anything below fails.
        await self._challenges.discard(data.challenge_token)

        session, refresh_token = await self._user_service.start_session(
            updated_user,
            challenge.device_info,
        )
        await self._uow.commit()

        return CompleteTwoFactorOutput(
            user_id=updated_user.id.to_raw(),
            session_id=str(session.session_id),
            refresh_token=refresh_token,
            login_challenge=challenge.login_challenge,
        )
