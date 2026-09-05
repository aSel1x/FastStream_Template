from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from litestar.connection import Request
from litestar.enums import ScopeType
from litestar.exceptions import NotAuthorizedException
from litestar.security.jwt import Token
from litestar.testing import RequestFactory

from infrastructure.hydra.config import HydraConfig
from infrastructure.hydra.schemas import HydraIntrospection
from presentation.http.di_state import DishkaState
from presentation.http.security import (
    HydraIntrospectionMiddleware,
    UserSecuritySchema,
    retrieve_user_handler,
)


async def _noop_app(scope, receive, send) -> None:
    return None


def _make_middleware() -> HydraIntrospectionMiddleware:
    return HydraIntrospectionMiddleware(
        algorithm='RS256',
        app=_noop_app,
        auth_header='Authorization',
        exclude=None,
        exclude_http_methods=None,
        exclude_opt_key='exclude_from_auth',
        retrieve_user_handler=retrieve_user_handler,
        scopes={ScopeType.HTTP},
        token_secret='',
    )


def _make_connection(
    cache: AsyncMock, hydra_client: AsyncMock, config: HydraConfig
) -> Request[UserSecuritySchema, Token, DishkaState]:
    """A real ASGIConnection carrying a stub dishka container.

    Built from an ASGI scope rather than faked with SimpleNamespace: the middleware takes a
    concrete Litestar type, so a look-alike only type-checks by accident.
    """
    registry: dict[str, object] = {
        'HydraAdminClient': hydra_client,
        'CacheInterface': cache,
        'HydraConfig': config,
    }

    async def resolve(cls: type[object], component: str = '') -> object:
        return registry[cls.__name__]

    connection: Request[UserSecuritySchema, Token, DishkaState] = RequestFactory().get('/')
    # `setup_dishka` attaches the container at runtime; a stub with just `get` is all the
    # middleware touches, and there is no public way to build a real container of doubles.
    connection.state.dishka_container = SimpleNamespace(get=resolve)  # pyright: ignore[reportAttributeAccessIssue]
    return connection


class TestHydraIntrospectionMiddleware:
    @pytest.mark.asyncio
    async def test_cache_miss_calls_introspection_and_populates_cache(self):
        user_id = uuid4()
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        hydra_client = AsyncMock()
        hydra_client.introspect_token = AsyncMock(
            return_value=HydraIntrospection(
                active=True,
                sub=str(user_id),
                client_id='client-1',
                scope='openid profile',
                aud=[],
                exp=9999999999,
                iat=1,
                token_type='access_token',
                ext={'session_id': 'sess-1'},
            )
        )
        config = HydraConfig(introspection_cache_ttl_seconds=30)
        connection = _make_connection(cache, hydra_client, config)

        middleware = _make_middleware()
        result = await middleware.authenticate_token('some-token', connection)

        hydra_client.introspect_token.assert_awaited_once_with('some-token')
        cache.set.assert_awaited_once()
        assert result.user.user_id == user_id
        assert result.auth.extras['session_id'] == 'sess-1'
        assert result.auth.extras['client_id'] == 'client-1'

    @pytest.mark.asyncio
    async def test_cache_hit_skips_introspection_call(self):
        import json
        from uuid import uuid4

        user_id = str(uuid4())
        cache = AsyncMock()
        cache.get = AsyncMock(
            return_value=json.dumps(
                {
                    'active': True,
                    'sub': user_id,
                    'client_id': 'client-1',
                    'scope': 'openid',
                    'aud': [],
                    'exp': 9999999999,
                    'iat': 1,
                    'token_type': 'access_token',
                    'ext': {},
                }
            )
        )
        hydra_client = AsyncMock()
        config = HydraConfig()
        connection = _make_connection(cache, hydra_client, config)

        middleware = _make_middleware()
        await middleware.authenticate_token('cached-token', connection)

        hydra_client.introspect_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_inactive_token_raises_not_authorized(self):
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        hydra_client = AsyncMock()
        hydra_client.introspect_token = AsyncMock(
            return_value=HydraIntrospection(
                active=False,
                sub=None,
                client_id=None,
                scope='',
                aud=[],
                exp=None,
                iat=None,
                token_type=None,
            )
        )
        config = HydraConfig(introspection_negative_cache_ttl_seconds=10)
        connection = _make_connection(cache, hydra_client, config)

        middleware = _make_middleware()
        with pytest.raises(NotAuthorizedException):
            await middleware.authenticate_token('revoked-token', connection)

        cache.set.assert_awaited_once()
        assert cache.set.await_args.kwargs['ttl_seconds'] == 10
