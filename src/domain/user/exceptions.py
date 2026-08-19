from dataclasses import dataclass
from typing import ClassVar, override
from uuid import UUID

from domain.common.exceptions import BaseDomainError

# Plain HTTP status ints (no framework import — domain stays framework-free); the presentation
# layer's exception handlers read `.status` off these via getattr.
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_LOCKED = 423


@dataclass(eq=False)
class UserIsDeletedError(BaseDomainError):
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
    message: str | None = None

    @property
    @override
    def detail(self) -> str:
        return self.message or 'Invalid username/email or password'


@dataclass(eq=False)
class UserNotFoundError(BaseDomainError):
    status: ClassVar[int] = _HTTP_NOT_FOUND
    user_id: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.user_id is None:
            return 'User not found'
        return f'User with "{self.user_id}" not found'


@dataclass(eq=False)
class InvalidTokenError(BaseDomainError):
    message: str | None = None

    @property
    @override
    def detail(self) -> str:
        return self.message or 'Invalid or expired token'


@dataclass(eq=False)
class AccountLockedError(BaseDomainError):
    status: ClassVar[int] = _HTTP_LOCKED
    user_id: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.user_id is None:
            return 'Account is locked'
        return f'Account with "{self.user_id}" is locked due to too many failed login attempts'


@dataclass(eq=False)
class EmailNotVerifiedError(BaseDomainError):
    @property
    @override
    def detail(self) -> str:
        return 'Email not verified'


@dataclass(eq=False)
class PasswordResetExpiredError(BaseDomainError):
    @property
    @override
    def detail(self) -> str:
        return 'Password reset token has expired'


@dataclass(eq=False)
class PermissionDeniedError(BaseDomainError):
    status: ClassVar[int] = _HTTP_FORBIDDEN
    permission: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.permission is None:
            return 'Permission denied'
        return f'Permission "{self.permission}" denied'


@dataclass(eq=False)
class RoleNotFoundError(BaseDomainError):
    status: ClassVar[int] = _HTTP_NOT_FOUND
    role_id: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.role_id is None:
            return 'Role not found'
        return f'Role "{self.role_id}" not found'


@dataclass(eq=False)
class RoleAlreadyExistsError(BaseDomainError):
    role_name: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.role_name is None:
            return 'Role already exists'
        return f'Role "{self.role_name}" already exists'