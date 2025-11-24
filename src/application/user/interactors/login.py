import logging
from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.user.interfaces import JWTInterface
from domain.user.service import UserService
from domain.user.value_objects import PlainPassword

from application.common.dto import BaseDTO
from application.common.interfaces import (
    EventPublisherInterface,
    InteractorInterface,
    UnitOfWorkInterface,
)

logger = logging.getLogger(__name__)


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
    user_id: UUID
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class LoginInteractor(InteractorInterface[LoginInputDTO, LoginOutputDTO]):
    def __init__(
        self,
        uow: UnitOfWorkInterface,
        user_service: UserService,
        jwt_service: JWTInterface,
        event_publisher: EventPublisherInterface,
    ) -> None:
        self._uow: UnitOfWorkInterface = uow
        self._user_service: UserService = user_service
        self._jwt_service: JWTInterface = jwt_service
        self._event_publisher: EventPublisherInterface = event_publisher

    @override
    async def __call__(self, dto: LoginInputDTO) -> LoginOutputDTO:
        plain_password = PlainPassword(dto.password)

        user = await self._user_service.authenticate(
            password=plain_password,
            username=dto.username,
            email=dto.email,
        )

        await self._uow.commit()

        logger.info(f'User {user.id.to_raw()} logged in successfully')

        user_payload = {'sub': str(user.id.to_raw())}

        access_token = await self._jwt_service.generate(
            user_payload, self._jwt_service.access_token_exp
        )
        refresh_token = await self._jwt_service.generate(
            user_payload, self._jwt_service.refresh_token_exp
        )

        await self._event_publisher.publish(self._user_service.pull_events())

        return LoginOutputDTO(
            user_id=user.id.to_raw(),
            access_token=access_token,
            token_type='Bearer',
            expires_in=self._jwt_service.access_token_exp,
            refresh_token=refresh_token,
        )
