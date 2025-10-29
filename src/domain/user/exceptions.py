from dataclasses import dataclass
from typing import override
from uuid import UUID

from domain.common.exception import BaseDomainError

# pyright: reportUnsafeMultipleInheritance=false


@dataclass(eq=False)
class UserIsDeletedError(RuntimeError, BaseDomainError):
    user_id: UUID

    @property
    @override
    def detail(self) -> str:
        return f'The user with "{self.user_id}" user_id is deleted'


@dataclass(eq=False)
class UsernameAlreadyExistsError(BaseDomainError):
    username: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.username is None:
            return 'A user with the username already exists'
        return f'A user with the "{self.username}" username already exists'


@dataclass(eq=False)
class EmailAlreadyExistsError(BaseDomainError):
    email: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.email is None:
            return 'A user with the email already exists'
        return f'A user with the "{self.email}" email already exists'


@dataclass(eq=False)
class InvalidCredentialsError(BaseDomainError):
    @property
    @override
    def detail(self) -> str:
        return 'Invalid username/email or password'


@dataclass(eq=False)
class UserNotFoundError(BaseDomainError):
    username_or_email: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.username_or_email is None:
            return 'User not found'
        return f'User with "{self.username_or_email}" not found'


@dataclass(eq=False)
class InvalidTokenError(BaseDomainError):
    @property
    @override
    def detail(self) -> str:
        return 'Invalid or expired token'


@dataclass(eq=False)
class UserIdNotExistError(BaseDomainError):
    user_id: UUID | None = None

    @property
    @override
    def detail(self) -> str:
        if self.user_id is None:
            return 'User with provided ID does not exist'
        return f'User with ID "{self.user_id}" does not exist'
