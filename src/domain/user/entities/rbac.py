import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import ClassVar, Self, override
from uuid import uuid4

from domain.common.entity import BaseEntity
from domain.common.event_dispatcher import DomainEventDispatcher
from domain.common.exceptions import BaseDomainError
from domain.common.value_object import BaseValueObject
from domain.user.events import RoleCreatedEvent, RoleDeletedEvent, RoleUpdatedEvent
from domain.user.value_objects import RoleID, RoleName, UserID

PERMISSION_NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_:.-]{1,63}$')


@dataclass(eq=False)
class WrongPermissionNameError(BaseDomainError):
    status: ClassVar[int] = 400
    name: str

    @property
    @override
    def detail(self) -> str:
        return f'Invalid permission name "{self.name}"'


@dataclass(frozen=True)
class Permission(BaseValueObject):
    name: str
    description: str | None = None

    @override
    def _validate(self) -> None:
        if not PERMISSION_NAME_PATTERN.match(self.name):
            raise WrongPermissionNameError(self.name)


@dataclass(frozen=True, kw_only=True, eq=False)
class Role(DomainEventDispatcher, BaseEntity):
    role_id: RoleID
    name: RoleName
    description: str | None = None
    permissions: tuple[Permission, ...] = field(default_factory=tuple)

    @override
    def _identity(self) -> object:
        return self.role_id

    @classmethod
    def create(
        cls,
        name: RoleName,
        description: str | None = None,
    ) -> Self:
        role = cls(
            role_id=RoleID(uuid4()),
            name=name,
            description=description,
        )
        role._record_event(RoleCreatedEvent(role_id=role.role_id.to_raw(), name=name.to_raw()))
        return role

    def has_permission(self, permission_name: str) -> bool:
        return any(p.name == permission_name for p in self.permissions)

    def add_permission(self, permission: Permission) -> Self:
        if self.has_permission(permission.name):
            return self
        role = self._with(permissions=(*self.permissions, permission))
        role._record_event(
            RoleUpdatedEvent(role_id=self.role_id.to_raw(), updated_fields=('permissions',))
        )
        return role

    def remove_permission(self, permission_name: str) -> Self:
        new_permissions = tuple(p for p in self.permissions if p.name != permission_name)
        role = self._with(permissions=new_permissions)
        if len(new_permissions) != len(self.permissions):
            role._record_event(
                RoleUpdatedEvent(role_id=self.role_id.to_raw(), updated_fields=('permissions',))
            )
        return role

    def update(self, name: RoleName | None = None, description: str | None = None) -> Self:
        updated_fields: list[str] = []
        changes: dict[str, object] = {}
        if name is not None and name.to_raw() != self.name.to_raw():
            changes['name'] = name
            updated_fields.append('name')
        if description is not None and description != self.description:
            changes['description'] = description
            updated_fields.append('description')
        if not updated_fields:
            return self
        role = self._with(**changes)
        role._record_event(
            RoleUpdatedEvent(role_id=self.role_id.to_raw(), updated_fields=tuple(updated_fields))
        )
        return role

    def delete(self) -> Self:
        role = self._with()
        role._record_event(RoleDeletedEvent(role_id=self.role_id.to_raw()))
        return role


@dataclass(frozen=True, eq=False)
class UserRole(BaseEntity):
    user_id: UserID
    role_id: RoleID
    assigned_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    assigned_by: UserID | None = None

    @override
    def _identity(self) -> object:
        return (self.user_id, self.role_id)
