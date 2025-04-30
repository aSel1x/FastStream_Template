import sqlalchemy as sa
from domain.user import entities
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.db.sqlalchemy.models.base import (
    AuditMixin,
    BaseModel,
    UUIDMixin,
    mapper_registry,
)


class UserModel(UUIDMixin, AuditMixin, BaseModel):
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    hashed_password: Mapped[bytes] = mapped_column(sa.LargeBinary, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


mapper_registry.map_imperatively(
    entities.User,
    UserModel.__table__,
    properties={
        'uuid': UserModel.uuid,
        'created_at': UserModel.created_at,
        'updated_at': UserModel.updated_at,
        'username': UserModel.username,
        'hashed_password': UserModel.hashed_password,
        'is_active': UserModel.is_active,
    },
    column_prefix='_',
)
