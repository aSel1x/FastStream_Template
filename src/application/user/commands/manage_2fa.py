from typing import final
from dataclasses import dataclass
from uuid import UUID

from application.common.interfaces import UnitOfWorkInterface
from application.user.services import UserService
from domain.user.exceptions import InvalidCredentialsError
from domain.user.interfaces import CryptInterface, TwoFactorInterface, UserRepositoryInterface
from domain.user.value_objects import PlainPassword, UserID


@dataclass
class Enable2FAOutput:
    secret: str
    backup_codes: list[str]
    provisioning_uri: str


@final
class Enable2FAUseCase:
    def __init__(
        self,
        user_service: UserService,
        two_factor: TwoFactorInterface,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._two_factor = two_factor
        self._uow = uow

    async def __call__(self, user_id: UUID) -> Enable2FAOutput:
        user = await self._user_service.get_user_by_id(UserID(user_id))
        enabled = user.enable_two_factor(self._two_factor)
        _ = await self._user_service.update_user(enabled)
        self._uow.add_events(enabled.pull_events())
        await self._uow.commit()

        secret_vo = enabled.two_factor_secret
        if secret_vo is None:
            raise RuntimeError("2FA secret not set after enable")
        return Enable2FAOutput(
            secret=secret_vo.secret,
            backup_codes=list(secret_vo.backup_codes),
            provisioning_uri=self._two_factor.get_provisioning_uri(
                secret_vo.secret, user.username.to_raw(),
            ),
        )


@final
class Disable2FAUseCase:
    def __init__(
        self,
        user_service: UserService,
        crypt: CryptInterface,
        uow: UnitOfWorkInterface,
    ) -> None:
        self._user_service = user_service
        self._crypt = crypt
        self._uow = uow

    async def __call__(self, user_id: UUID, current_password: str) -> None:
        user = await self._user_service.get_user_by_id(UserID(user_id))
        if not await user.verify_password(PlainPassword(current_password), self._crypt):
            raise InvalidCredentialsError('Invalid current password')

        disabled = user.disable_two_factor()
        _ = await self._user_service.update_user(disabled)
        self._uow.add_events(disabled.pull_events())
        await self._uow.commit()


@dataclass
class Verify2FAInput:
    code: str


@dataclass
class Verify2FAOutput:
    success: bool


@final
class Verify2FAUseCase:
    def __init__(
        self, user_repo: UserRepositoryInterface, two_factor: TwoFactorInterface, uow: UnitOfWorkInterface,
    ) -> None:
        self._user_repo = user_repo
        self._two_factor = two_factor
        self._uow = uow

    async def __call__(self, user_id: UUID, input: Verify2FAInput) -> Verify2FAOutput:
        user = await self._user_repo.acquire_by_id(UserID(user_id))
        if user is None:
            return Verify2FAOutput(success=False)

        success, updated = user.verify_two_factor(input.code, self._two_factor)
        if updated is not user:
            await self._user_repo.update(updated)
            await self._uow.commit()

        return Verify2FAOutput(success=success)
