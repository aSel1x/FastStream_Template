from dataclasses import dataclass

from domain.common.entity import AuditMixin, BaseEntity, UUIDMixin


@dataclass
class User(BaseEntity, UUIDMixin, AuditMixin):
    username: str
    hashed_password: bytes
    is_active: bool = True
