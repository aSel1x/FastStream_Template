from dataclasses import dataclass
from datetime import datetime
from typing import override
from uuid import UUID

from domain.common.event import BaseEvent
from domain.common.json_value import JsonValue


@dataclass
class UserCreatedEvent(BaseEvent):
    user_id: UUID
    username: str
    email: str | None

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id), 'username': self.username, 'email': self.email}


@dataclass
class UserAuthenticatedEvent(BaseEvent):
    user_id: UUID
    username: str

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id), 'username': self.username}


@dataclass
class UserProfileUpdatedEvent(BaseEvent):
    user_id: UUID
    updated_fields: tuple[str, ...]

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id), 'updated_fields': list(self.updated_fields)}


@dataclass
class UserDeletedEvent(BaseEvent):
    user_id: UUID

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id)}


@dataclass
class SessionCreatedEvent(BaseEvent):
    session_id: UUID
    user_id: UUID
    device_info: dict[str, str | None]

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {
            'session_id': str(self.session_id),
            'user_id': str(self.user_id),
            'device_info': dict(self.device_info),
        }


@dataclass
class SessionRevokedEvent(BaseEvent):
    session_id: UUID
    user_id: UUID

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'session_id': str(self.session_id), 'user_id': str(self.user_id)}


@dataclass
class TokenRefreshedEvent(BaseEvent):
    session_id: UUID
    user_id: UUID

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'session_id': str(self.session_id), 'user_id': str(self.user_id)}


@dataclass
class RoleCreatedEvent(BaseEvent):
    role_id: UUID
    name: str

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'role_id': str(self.role_id), 'name': self.name}


@dataclass
class RoleUpdatedEvent(BaseEvent):
    role_id: UUID
    updated_fields: tuple[str, ...]

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'role_id': str(self.role_id), 'updated_fields': list(self.updated_fields)}


@dataclass
class RoleDeletedEvent(BaseEvent):
    role_id: UUID

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'role_id': str(self.role_id)}


@dataclass
class UserRoleAssignedEvent(BaseEvent):
    user_id: UUID
    role_id: UUID
    assigned_by: UUID | None

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {
            'user_id': str(self.user_id),
            'role_id': str(self.role_id),
            'assigned_by': str(self.assigned_by) if self.assigned_by else None,
        }


@dataclass
class UserRoleRevokedEvent(BaseEvent):
    user_id: UUID
    role_id: UUID
    revoked_by: UUID | None

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {
            'user_id': str(self.user_id),
            'role_id': str(self.role_id),
            'revoked_by': str(self.revoked_by) if self.revoked_by else None,
        }


@dataclass
class AccountLockedEvent(BaseEvent):
    user_id: UUID
    reason: str
    locked_until: datetime | None

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {
            'user_id': str(self.user_id),
            'reason': self.reason,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
        }


@dataclass
class AccountUnlockedEvent(BaseEvent):
    user_id: UUID

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id)}


@dataclass
class PasswordResetRequestedEvent(BaseEvent):
    user_id: UUID
    email: str
    reset_token: str

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id), 'email': self.email, 'reset_token': self.reset_token}


@dataclass
class PasswordResetCompletedEvent(BaseEvent):
    user_id: UUID

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id)}


@dataclass
class PasswordChangedEvent(BaseEvent):
    user_id: UUID

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id)}


@dataclass
class EmailVerificationRequestedEvent(BaseEvent):
    user_id: UUID
    email: str
    verification_token: str

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {
            'user_id': str(self.user_id),
            'email': self.email,
            'verification_token': self.verification_token,
        }


@dataclass
class EmailVerifiedEvent(BaseEvent):
    user_id: UUID
    email: str

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id), 'email': self.email}


@dataclass
class TwoFactorEnabledEvent(BaseEvent):
    user_id: UUID
    backup_codes: tuple[str, ...]

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id), 'backup_codes': list(self.backup_codes)}


@dataclass
class TwoFactorDisabledEvent(BaseEvent):
    user_id: UUID

    @override
    def to_payload(self) -> dict[str, JsonValue]:
        return {'user_id': str(self.user_id)}


_EVENT_AGGREGATE: dict[str, tuple[str, str]] = {
    'UserCreatedEvent': ('User', 'user_id'),
    'UserAuthenticatedEvent': ('User', 'user_id'),
    'UserProfileUpdatedEvent': ('User', 'user_id'),
    'UserDeletedEvent': ('User', 'user_id'),
    'AccountLockedEvent': ('User', 'user_id'),
    'AccountUnlockedEvent': ('User', 'user_id'),
    'PasswordResetRequestedEvent': ('User', 'user_id'),
    'PasswordResetCompletedEvent': ('User', 'user_id'),
    'PasswordChangedEvent': ('User', 'user_id'),
    'EmailVerificationRequestedEvent': ('User', 'user_id'),
    'EmailVerifiedEvent': ('User', 'user_id'),
    'TwoFactorEnabledEvent': ('User', 'user_id'),
    'TwoFactorDisabledEvent': ('User', 'user_id'),
    'SessionCreatedEvent': ('Session', 'session_id'),
    'SessionRevokedEvent': ('Session', 'session_id'),
    'TokenRefreshedEvent': ('Session', 'session_id'),
    'RoleCreatedEvent': ('Role', 'role_id'),
    'RoleUpdatedEvent': ('Role', 'role_id'),
    'RoleDeletedEvent': ('Role', 'role_id'),
    'UserRoleAssignedEvent': ('Role', 'role_id'),
    'UserRoleRevokedEvent': ('Role', 'role_id'),
}


def event_aggregate(event: BaseEvent) -> tuple[str, UUID | None]:
    """Return the (aggregate_type, aggregate_id) a domain event belongs to, for outbox/audit persistence."""
    aggregate_type, id_field = _EVENT_AGGREGATE.get(type(event).__name__, ('Unknown', ''))
    if not id_field:
        return aggregate_type, None
    aggregate_id = event.to_payload().get(id_field)
    return aggregate_type, UUID(aggregate_id) if isinstance(aggregate_id, str) else None
