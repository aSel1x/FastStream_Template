from dataclasses import dataclass
from typing import ClassVar, override
from uuid import UUID

from domain.common.exceptions import BaseDomainError

# Plain HTTP status ints (no framework import — domain stays framework-free); the presentation
# layer's exception handlers read `.status` off these via getattr.
_HTTP_BAD_REQUEST = 400
_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_CONFLICT = 409
_HTTP_LOCKED = 423


@dataclass(eq=False)
class UserIsDeletedError(BaseDomainError):
    status: ClassVar[int] = _HTTP_FORBIDDEN
    user_id: UUID

    @property
    @override
    def detail(self) -> str:
        return f'The user with "{self.user_id}" user_id is deleted'


@dataclass(eq=False)
class UsernameAlreadyExistsError(BaseDomainError):
    status: ClassVar[int] = _HTTP_CONFLICT
    username: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.username is None:
            return 'A user with the username already exists'
        return f'A user with the "{self.username}" username already exists'


@dataclass(eq=False)
class EmailAlreadyExistsError(BaseDomainError):
    status: ClassVar[int] = _HTTP_CONFLICT
    email: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.email is None:
            return 'A user with the email already exists'
        return f'A user with the "{self.email}" email already exists'


@dataclass(eq=False)
class InvalidCredentialsError(BaseDomainError):
    status: ClassVar[int] = _HTTP_UNAUTHORIZED
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
    status: ClassVar[int] = _HTTP_BAD_REQUEST
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
        # Never interpolate the id: this reaches an unauthenticated caller, and the internal
        # user UUID is exactly what an enumeration attempt is looking for. It stays on the
        # exception for logging.
        return 'Account is locked due to too many failed login attempts'


@dataclass(eq=False)
class EmailNotVerifiedError(BaseDomainError):
    status: ClassVar[int] = _HTTP_FORBIDDEN

    @property
    @override
    def detail(self) -> str:
        return 'Email not verified'


@dataclass(eq=False)
class PasswordResetExpiredError(BaseDomainError):
    status: ClassVar[int] = _HTTP_BAD_REQUEST

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
    status: ClassVar[int] = _HTTP_CONFLICT
    role_name: str | None = None

    @property
    @override
    def detail(self) -> str:
        if self.role_name is None:
            return 'Role already exists'
        return f'Role "{self.role_name}" already exists'


@dataclass(eq=False)
class TwoFactorAlreadyEnabledError(BaseDomainError):
    status: ClassVar[int] = _HTTP_CONFLICT

    @property
    @override
    def detail(self) -> str:
        return 'Two-factor authentication is already enabled; disable it first to re-enrol'


@dataclass(eq=False)
class TwoFactorNotEnrolledError(BaseDomainError):
    status: ClassVar[int] = _HTTP_BAD_REQUEST

    @property
    @override
    def detail(self) -> str:
        return 'Two-factor authentication is not enrolled'


@dataclass(eq=False)
class ConcurrentModificationError(BaseDomainError):
    """Someone else wrote this aggregate first.

    Raised when an optimistic-lock update matches no row. Retrying the operation on freshly
    loaded state is the correct response.
    """

    status: ClassVar[int] = _HTTP_CONFLICT
    entity_id: str | None = None

    @property
    @override
    def detail(self) -> str:
        return 'The record was modified concurrently; please retry'


@dataclass(eq=False)
class RefreshTokenReuseError(BaseDomainError):
    """A refresh token that had already been rotated away was presented again.

    Treated as a leak rather than a mistake: the whole session is revoked, since a legitimate
    client never replays a token it has already exchanged.
    """

    status: ClassVar[int] = _HTTP_UNAUTHORIZED

    @property
    @override
    def detail(self) -> str:
        return 'Refresh token was already used; the session has been revoked'
