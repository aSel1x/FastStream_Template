from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from domain.audit.entities.audit_log import AuditLog


class AuditRepositoryInterface(Protocol):
    async def add(self, log: AuditLog) -> None: ...

    async def get_by_user_id(self, user_id: UUID, limit: int = 100) -> list[AuditLog]: ...

    async def get_by_entity(self, entity_type: str, entity_id: UUID, limit: int = 100) -> list[AuditLog]: ...
