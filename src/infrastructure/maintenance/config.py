from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class MaintenanceConfig:
    """How long each kind of row is kept.

    Nothing in this service used to delete anything on a schedule: expired sessions, processed
    outbox rows, soft-deleted users and audit entries all accumulated forever.
    """

    interval_seconds: int = 3600
    session_grace_days: int = 7
    outbox_retention_days: int = 7
    audit_retention_days: int = 365
    #: How long a soft-deleted account is kept before it is anonymised. Long enough for the
    #: user to change their mind and for any dispute to surface.
    deleted_user_retention_days: int = 30
    dry_run: bool = False

    @classmethod
    def from_environ(cls) -> MaintenanceConfig:
        return cls(
            interval_seconds=int(getenv('MAINTENANCE_INTERVAL_SECONDS', '3600')),
            session_grace_days=int(getenv('MAINTENANCE_SESSION_GRACE_DAYS', '7')),
            outbox_retention_days=int(getenv('MAINTENANCE_OUTBOX_RETENTION_DAYS', '7')),
            audit_retention_days=int(getenv('MAINTENANCE_AUDIT_RETENTION_DAYS', '365')),
            deleted_user_retention_days=int(getenv('MAINTENANCE_DELETED_USER_DAYS', '30')),
            dry_run=getenv('MAINTENANCE_DRY_RUN', 'false').lower() == 'true',
        )
