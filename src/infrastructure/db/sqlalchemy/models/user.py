from domain.user import entities
from domain.user import value_objects as vo
from infrastructure.db.sqlalchemy.models.base import (
    AuditMixin,
    UUIDMixin,
    create_mapping,
    create_table,
)

import sqlalchemy as sa
from sqlalchemy.orm import composite

USERS_TABLE = create_table(
    'users',
    sa.Column('username', sa.String, unique=True, nullable=False),
    sa.Column('email', sa.String, unique=True, nullable=True),
    sa.Column('hashed_password', sa.LargeBinary, nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    mixins={UUIDMixin, AuditMixin},
)


_ = create_mapping(
    entities.User,
    USERS_TABLE,
    properties={
        'username': composite(vo.Username, USERS_TABLE.c.username),
        'email': composite(vo.Email, USERS_TABLE.c.email),
        'hashed_password': composite(vo.HashedPassword, USERS_TABLE.c.hashed_password),
        'deleted_at': composite(vo.DeletionTime, USERS_TABLE.c.deleted_at),
    },
    mixins={UUIDMixin, AuditMixin},
)
