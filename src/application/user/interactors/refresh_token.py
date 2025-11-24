import logging
from dataclasses import dataclass
from typing import override

from domain.user.exceptions import InvalidTokenError
from domain.user.interfaces import JWTInterface

from application.common.dto import BaseDTO
from application.common.interfaces import InteractorInterface

logger = logging.getLogger(__name__)


@dataclass
class RefreshTokenInputDTO(BaseDTO):
    refresh_token: str


@dataclass
class RefreshTokenOutputDTO(BaseDTO):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str


class RefreshTokenInteractor(
    InteractorInterface[RefreshTokenInputDTO, RefreshTokenOutputDTO]
):
    def __init__(
        self,
        jwt_service: JWTInterface,
    ) -> None:
        self._jwt_service: JWTInterface = jwt_service

    @override
    async def __call__(self, dto: RefreshTokenInputDTO) -> RefreshTokenOutputDTO:
        try:
            payload = await self._jwt_service.extract(dto.refresh_token)
        except InvalidTokenError:
            logger.warning('Invalid or expired refresh token')
            raise

        user_id = payload.get('sub')
        if not user_id:
            logger.warning('Refresh token missing user_id')
            raise InvalidTokenError()

        logger.info(f'Refreshing tokens for user {user_id}')

        user_payload = {'user_id': user_id}

        access_token = await self._jwt_service.generate(
            user_payload, self._jwt_service.access_token_exp
        )
        refresh_token = await self._jwt_service.generate(
            user_payload, self._jwt_service.refresh_token_exp
        )

        return RefreshTokenOutputDTO(
            access_token=access_token,
            token_type='Bearer',
            expires_in=self._jwt_service.access_token_exp,
            refresh_token=refresh_token,
        )
