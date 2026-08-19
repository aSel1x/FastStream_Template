import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import override
from uuid import UUID

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.middleware.authentication import AuthenticationResult
from litestar.security.jwt import JWTAuth, Token
from litestar.security.jwt.middleware import JWTAuthenticationMiddleware
from pydantic import ValidationError

from application.common.interfaces.system.cache import CacheInterface
from infrastructure.hydra import HydraAdminClient, HydraConfig
from infrastructure.hydra.schemas import HydraIntrospection
from presentation.http.di_state import DishkaState


@dataclass
class UserSecuritySchema:
    user_id: UUID
    scopes: set[str] = field(default_factory=set)


async def retrieve_user_handler(
    token: Token, _connection: ASGIConnection[object, UserSecuritySchema, Token, DishkaState]
) -> UserSecuritySchema:
    user_id = UUID(token.sub)
    scopes_raw = token.extras.get('scopes') if token.extras else None
    scopes_str = scopes_raw if isinstance(scopes_raw, str) else ''
    return UserSecuritySchema(user_id=user_id, scopes=set(scopes_str.split()) if scopes_str else set())


def _introspection_cache_key(token: str) -> str:
    return f'hydra:introspect:{hashlib.sha256(token.encode()).hexdigest()}'


class HydraIntrospectionMiddleware(JWTAuthenticationMiddleware):
    @override
    async def authenticate_token(
        self, encoded_token: str, connection: ASGIConnection[object, UserSecuritySchema, Token, DishkaState]
    ) -> AuthenticationResult:
        container = connection.state.dishka_container
        hydra_client = await container.get(HydraAdminClient)
        cache = await container.get(CacheInterface)
        config = await container.get(HydraConfig)

        cache_key = _introspection_cache_key(encoded_token)
        cached = await cache.get(cache_key)
        if cached is not None:
            try:
                introspection = HydraIntrospection.model_validate_json(cached)
            except ValidationError as e:
                raise NotAuthorizedException() from e
        else:
            introspection = await hydra_client.introspect_token(encoded_token)
            ttl = (
                config.introspection_cache_ttl_seconds
                if introspection.active
                else config.introspection_negative_cache_ttl_seconds
            )
            await cache.set(cache_key, introspection.model_dump_json(), ttl_seconds=ttl)

        if not introspection.active or not introspection.sub:
            raise NotAuthorizedException()

        now = datetime.now(UTC)
        exp = datetime.fromtimestamp(introspection.exp, tz=UTC) if introspection.exp else now + timedelta(minutes=5)
        iat = datetime.fromtimestamp(introspection.iat, tz=UTC) if introspection.iat else now

        session_id = introspection.ext.get('session_id', '')

        token = Token(
            sub=introspection.sub,
            exp=exp,
            iat=iat,
            extras={
                'scopes': introspection.scope,
                'session_id': session_id if isinstance(session_id, str) else '',
                'client_id': introspection.client_id or '',
            },
        )

        user = await retrieve_user_handler(token, connection)
        if not user:
            raise NotAuthorizedException()
        return AuthenticationResult(user=user, auth=token)


def create_hydra_auth() -> JWTAuth[UserSecuritySchema]:
    exclude_paths = [
        '/health',
        '/v1/users/login',
        '/v1/users/register',
        '/v1/auth/refresh',
        '/v1/auth/request-password-reset',
        '/v1/auth/reset-password',
        '/schema',
        '/auth/login',
        '/auth/consent',
        '/auth/logout',
    ]

    auth = JWTAuth[UserSecuritySchema](
        retrieve_user_handler=retrieve_user_handler,
        token_secret='',
        algorithm='RS256',
        exclude=exclude_paths,
        authentication_middleware_class=HydraIntrospectionMiddleware,
    )
    return auth
