from __future__ import annotations

from typing import TYPE_CHECKING, override

from domain.user.exceptions import InvalidTokenError
from litestar.connection import ASGIConnection
from litestar.datastructures.state import State
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from litestar.types import ASGIApp

if TYPE_CHECKING:
    from domain.user.interfaces import JWTInterface


class JWTAuthMiddleware(AbstractAuthenticationMiddleware):
    _jwt_service: JWTInterface

    def __init__(self, app: ASGIApp, jwt_service: JWTInterface) -> None:
        super().__init__(app)
        self._jwt_service = jwt_service

    @override
    async def authenticate_request(
        self, connection: ASGIConnection[object, object, object, State]
    ) -> AuthenticationResult:
        auth_header = connection.headers.get('Authorization')

        if not auth_header:
            return AuthenticationResult(user=None, auth=None)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return AuthenticationResult(user=None, auth=None)

        token = parts[1]

        try:
            payload = await self._jwt_service.extract(token)
            user_id = payload.get('user_id')

            if not user_id:
                return AuthenticationResult(user=None, auth=None)

            connection.app.state.user_id = user_id

            return AuthenticationResult(user={'user_id': user_id}, auth=token)

        except InvalidTokenError:
            return AuthenticationResult(user=None, auth=None)
