from dataclasses import dataclass
from uuid import UUID

from litestar.connection import ASGIConnection
from litestar.datastructures.state import State
from litestar.security.jwt import JWTAuth, Token


@dataclass
class UserSecuritySchema:
    user_id: UUID


async def retrieve_user_handler(
    token: Token, _connection: ASGIConnection[object, UserSecuritySchema, Token, State]
) -> UserSecuritySchema:
    """Retrieve user from token payload."""
    user_id = UUID(token.sub)
    return UserSecuritySchema(user_id=user_id)


def create_jwt_auth(token_secret: str) -> JWTAuth[UserSecuritySchema]:
    """Create JWTAuth instance with the given secret and full typing."""
    return JWTAuth[UserSecuritySchema](
        retrieve_user_handler=retrieve_user_handler,
        token_secret=token_secret,
        exclude=['/users/login', '/users/register', '/schema'],
    )
