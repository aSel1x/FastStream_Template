from typing import final

from domain.audit.audit_action import AuditAction
from domain.audit.entities.audit_log import AuditLog
from domain.audit.interfaces.persistence.audit_repo import AuditRepositoryInterface
from domain.common.event import BaseEvent
from domain.user.events import (
    AccountLockedEvent,
    AccountUnlockedEvent,
    EmailVerifiedEvent,
    PasswordChangedEvent,
    PasswordResetCompletedEvent,
    RoleCreatedEvent,
    RoleDeletedEvent,
    RoleUpdatedEvent,
    SessionCreatedEvent,
    SessionRevokedEvent,
    TokenRefreshedEvent,
    TwoFactorDisabledEvent,
    TwoFactorEnabledEvent,
    UserAuthenticatedEvent,
    UserCreatedEvent,
    UserDeletedEvent,
    UserProfileUpdatedEvent,
    UserRoleAssignedEvent,
    UserRoleRevokedEvent,
    event_aggregate,
)

EVENT_TO_ACTION: dict[type[BaseEvent], str] = {
    UserCreatedEvent: AuditAction.USER_CREATED,
    UserAuthenticatedEvent: AuditAction.USER_LOGIN,
    UserProfileUpdatedEvent: AuditAction.USER_PROFILE_UPDATED,
    UserDeletedEvent: AuditAction.USER_DELETED,
    AccountLockedEvent: AuditAction.USER_LOCKED,
    AccountUnlockedEvent: AuditAction.USER_UNLOCKED,
    PasswordResetCompletedEvent: AuditAction.USER_PASSWORD_RESET,
    PasswordChangedEvent: AuditAction.USER_PASSWORD_CHANGED,
    EmailVerifiedEvent: AuditAction.USER_EMAIL_VERIFIED,
    TwoFactorEnabledEvent: AuditAction.USER_2FA_ENABLED,
    TwoFactorDisabledEvent: AuditAction.USER_2FA_DISABLED,
    SessionCreatedEvent: AuditAction.SESSION_CREATED,
    SessionRevokedEvent: AuditAction.SESSION_REVOKED,
    TokenRefreshedEvent: AuditAction.SESSION_REFRESHED,
    UserRoleAssignedEvent: AuditAction.ROLE_ASSIGNED,
    UserRoleRevokedEvent: AuditAction.ROLE_REVOKED,
    RoleCreatedEvent: AuditAction.ROLE_CREATED,
    RoleUpdatedEvent: AuditAction.ROLE_UPDATED,
    RoleDeletedEvent: AuditAction.ROLE_DELETED,
}
"""Which audit action each event records as, keyed on the class rather than its name."""


@final
class AuditEventHandler:
    def __init__(self, audit_repo: AuditRepositoryInterface) -> None:
        self._audit_repo = audit_repo

    async def handle(self, event: BaseEvent) -> None:
        entry = _event_to_audit(event)
        if entry is None:
            return
        await self._audit_repo.add(entry)

    async def handle_many(self, events: list[BaseEvent]) -> None:
        for event in events:
            await self.handle(event)


def _event_to_audit(event: BaseEvent) -> AuditLog | None:
    action = EVENT_TO_ACTION.get(type(event))
    if action is None:
        return None

    entity_type, entity_id = event_aggregate(event)
    return AuditLog.create(
        user_id=getattr(event, 'user_id', None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        success=True,
    )
