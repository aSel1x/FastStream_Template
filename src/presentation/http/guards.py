from collections.abc import Callable, Coroutine

from litestar.connection import ASGIConnection
from litestar.exceptions import PermissionDeniedException
from litestar.handlers.base import BaseRouteHandler
from litestar.security.jwt import Token

from application.user.queries.rbac import CheckPermissionUseCase
from presentation.http.di_state import DishkaState
from presentation.http.security import UserSecuritySchema

ADMIN_PERMISSION = 'admin'

# OAuth scopes. A token that survives introspection is only allowed to do what the user
# actually consented to; without a scope on a route, any 'openid'-only token from a low-trust
# third-party app could delete the account or disable the second factor.
SCOPE_PROFILE = 'profile'
SCOPE_ACCOUNT_WRITE = 'account:write'
SCOPE_SESSIONS_WRITE = 'sessions:write'


async def require_admin(
    connection: ASGIConnection[BaseRouteHandler, UserSecuritySchema, Token, DishkaState],
    _: BaseRouteHandler,
) -> None:
    user = connection.user
    check_permission = await connection.state.dishka_container.get(CheckPermissionUseCase)
    is_admin = await check_permission(user.user_id, ADMIN_PERMISSION)
    if not is_admin:
        raise PermissionDeniedException(detail='Admin permission required')


def require_scope(
    scope: str,
) -> Callable[
    [ASGIConnection[BaseRouteHandler, UserSecuritySchema, Token, DishkaState], BaseRouteHandler],
    Coroutine[None, None, None],
]:
    async def guard(
        connection: ASGIConnection[BaseRouteHandler, UserSecuritySchema, Token, DishkaState],
        _: BaseRouteHandler,
    ) -> None:
        if scope not in connection.user.scopes:
            raise PermissionDeniedException(detail=f'OAuth scope "{scope}" required')

    return guard
