from typing import Protocol

from domain.common.entity import EntityUUID
from domain.user.entities import User
from domain.user.value_objects import Email, Username


class UserRepositoryInterface(Protocol):
    """
    User repository interface.
    """

    async def acquire_by_uuid(self, user_id: EntityUUID) -> User | None:
        """
        Acquire a user by ID.
        """
        raise NotImplementedError

    async def acquire_by_username(self, username: Username) -> User | None:
        """
        Acquire a user by username.
        """
        raise NotImplementedError

    async def acquire_by_email(self, email: Email) -> User | None:
        """
        Acquire a user by email.
        """
        raise NotImplementedError

    async def add(self, user: User) -> None:
        """
        Add a new user.
        """
        raise NotImplementedError

    async def update(self, user: User) -> None:
        """
        Update existing user.
        """
        raise NotImplementedError

    async def check_username_exists(self, username: Username) -> bool:
        """
        Check if a username already exists.
        """
        raise NotImplementedError

    async def check_email_exists(self, email: Email) -> bool:
        """
        Check if an email already exists.
        """
        raise NotImplementedError
