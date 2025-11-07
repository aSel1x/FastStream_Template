import logging
from dataclasses import dataclass
from typing import override

from domain.user.interfaces import JWTInterface
from domain.user.service import UserService
from domain.user.value_objects import PlainPassword

from application.common.dto import BaseDTO
from application.common.interfaces import InteractorInterface, UnitOfWorkInterface

logger = logging.getLogger(__name__)


ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 15  # 15 minutes
REFRESH_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7  # 7 days


@dataclass
class LoginInputDTO(BaseDTO):
    password: str
    username: str | None = None
    email: str | None = None


@dataclass
class TokenInfoDTO(BaseDTO):
    """Token information response DTO (RFC 6749 OAuth 2.0)."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


@dataclass
class LoginOutputDTO(BaseDTO):
    user_id: str
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class LoginInteractor(InteractorInterface[LoginInputDTO, LoginOutputDTO]):
    _uow: UnitOfWorkInterface
    _user_service: UserService
    _jwt_service: JWTInterface

    def __init__(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
        jwt_service: JWTInterface,
    ) -> None:
        self._uow = uow
        self._user_service = user_service
        self._jwt_service = jwt_service

    @override
    async def __call__(self, dto: LoginInputDTO) -> LoginOutputDTO:
        plain_password = PlainPassword(dto.password)

        user = await self._user_service.authenticate(
            password=plain_password,
            username=dto.username,
            email=dto.email,
        )

        await self._uow.commit()

        logger.info(f'User {user.uuid} logged in successfully')

        user_payload = {'sub': str(user.uuid.to_raw())}

        access_token = await self._jwt_service.generate(
            user_payload, ACCESS_TOKEN_EXPIRE_SECONDS
        )
        refresh_token = await self._jwt_service.generate(
            user_payload, REFRESH_TOKEN_EXPIRE_SECONDS
        )

        return LoginOutputDTO(
            user_id=str(user.uuid.to_raw()),
            access_token=access_token,
            token_type='Bearer',
            expires_in=ACCESS_TOKEN_EXPIRE_SECONDS,
            refresh_token=refresh_token,
        )
