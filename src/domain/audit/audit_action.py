from enum import StrEnum


class AuditAction(StrEnum):
    USER_CREATED = 'user.created'
    USER_LOGIN = 'user.login'
    USER_LOGIN_FAILED = 'user.login_failed'
    USER_LOGOUT = 'user.logout'
    USER_PASSWORD_CHANGED = 'user.password_changed'  # noqa: S105 - an action name, not a secret
    USER_PASSWORD_RESET = 'user.password_reset'  # noqa: S105 - an action name, not a secret
    USER_EMAIL_VERIFIED = 'user.email_verified'
    USER_PROFILE_UPDATED = 'user.profile_updated'
    USER_DELETED = 'user.deleted'
    USER_LOCKED = 'user.locked'
    USER_UNLOCKED = 'user.unlocked'
    USER_2FA_ENABLED = 'user.two_factor_enabled'
    USER_2FA_DISABLED = 'user.two_factor_disabled'
    SESSION_CREATED = 'session.created'
    SESSION_REVOKED = 'session.revoked'
    SESSION_REFRESHED = 'session.refreshed'
    ROLE_ASSIGNED = 'role.assigned'
    ROLE_REVOKED = 'role.revoked'
    ROLE_CREATED = 'role.created'
    ROLE_UPDATED = 'role.updated'
    ROLE_DELETED = 'role.deleted'
    PERMISSION_GRANTED = 'permission.granted'
    PERMISSION_REVOKED = 'permission.revoked'
