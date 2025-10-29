from typing import Protocol

from domain.user.entities import User
from domain.user.value_objects import PlainPassword, Token, TokenResponse


class AuthenticationServiceInterface(Protocol):
    """
    Authentication service interface.
    Contains domain logic for authentication operations.
    """

    async def verify_password(self, plain_password: PlainPassword, user: User) -> bool:
        """
        Verify that plain password matches user's hashed password.
        Delegates to crypt interface but returns domain boolean.
        """
        raise NotImplementedError

    async def generate_tokens(self, user: User) -> TokenResponse:
        """
        Generate access and refresh tokens for user.
        Uses JWT interface to create tokens.
        """
        raise NotImplementedError

    async def verify_access_token(self, token: Token) -> dict[str, object]:
        """
        Verify and extract data from access token.
        Returns token payload if valid.
        """
        raise NotImplementedError

    async def verify_refresh_token(self, token: Token) -> dict[str, object]:
        """
        Verify and extract data from refresh token.
        Returns token payload if valid.
        """
        raise NotImplementedError
