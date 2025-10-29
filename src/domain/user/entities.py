from dataclasses import dataclass, field

from domain.common.entity import AuditMixin, BaseEntity, UUIDMixin
from domain.user.value_objects import DeletionTime, Email, HashedPassword, Username


@dataclass
class User(BaseEntity, UUIDMixin, AuditMixin):
    username: Username
    email: Email
    hashed_password: HashedPassword
    deleted_at: DeletionTime = field(
        default=DeletionTime.create_not_deleted(), kw_only=True
    )

    def is_deleted(self) -> bool:
        return self.deleted_at.is_deleted()

    def update_username(self, username: Username) -> None:
        self.username = username

    def update_email(self, email: Email) -> None:
        self.email = email
