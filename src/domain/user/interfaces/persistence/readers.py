from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from domain.user.entities.session import DeviceInfo
from domain.user.value_objects import TwoFactorSecret, UserID


@dataclass(frozen=True)
class UserReadDTO:
    user_id: UUID
    username: str
    email: str | None
    is_email_verified: bool
    is_locked: bool
    two_factor_secret: TwoFactorSecret | None


@dataclass(frozen=True)
class SessionReadDTO:
    session_id: UUID
    created_at: datetime
    expires_at: datetime
    is_revoked: bool
    device_info: DeviceInfo


@dataclass(frozen=True)
class RoleReadDTO:
    role_id: UUID
    name: str
    description: str | None = None
    permissions: tuple[str, ...] = ()


class UserReader(Protocol):
    async def get_by_id(self, user_id: UserID) -> UserReadDTO | None: ...


class SessionReader(Protocol):
    async def get_by_user_id(self, user_id: UserID) -> list[SessionReadDTO]: ...


class RoleReader(Protocol):
    async def get_user_roles(self, user_id: UserID) -> list[RoleReadDTO]: ...
    async def get_all_roles(self) -> list[RoleReadDTO]: ...
