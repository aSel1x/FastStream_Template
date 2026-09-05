from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from domain.user.value_objects import Email, TokenHash, UserID, Username

if TYPE_CHECKING:
    from domain.user.entities import User


class UserRepositoryInterface(Protocol):
    """User repository interface."""

    async def acquire_by_id(self, user_id: UserID) -> User | None:
        """Acquire a user by ID."""
        ...

    async def acquire_by_username(self, username: Username) -> User | None:
        """Acquire a user by username."""
        ...

    async def acquire_by_email(self, email: Email) -> User | None:
        """Acquire a user by email."""
        ...

    async def acquire_by_verification_token(self, token_hash: TokenHash) -> User | None:
        """Acquire a user by the hash of their email-verification token.

        Looking the user up *by* the token is what lets an emailed link work without the
        recipient being authenticated or having to supply their own id.
        """
        ...

    async def acquire_by_reset_token(self, token_hash: TokenHash) -> User | None:
        """Acquire a user by the hash of their password-reset token."""
        ...

    async def add(self, user: User) -> None:
        """Add a new user."""
        ...

    async def update(self, user: User) -> None:
        """Update existing user."""
        ...

    async def check_username_exists(self, username: Username) -> bool:
        """Check if a username already exists."""
        ...

    async def check_email_exists(self, email: Email) -> bool:
        """Check if an email already exists."""
        ...

    async def get_all_user_ids(self) -> list[str]:
        """Get all user IDs (for session refresh scanning)."""
        ...
