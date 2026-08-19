from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import override
from uuid import UUID, uuid4

from domain.common.entity import BaseEntity
from domain.common.json_value import JsonValue


@dataclass(frozen=True, eq=False)
class AuditLog(BaseEntity):
    id: UUID = field(default_factory=uuid4)
    user_id: UUID | None = None
    action: str = ''
    entity_type: str = ''
    entity_id: UUID | None = None
    details: dict[str, JsonValue] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    success: bool = True

    @override
    def _identity(self) -> object:
        return self.id

    @classmethod
    def create(
        cls,
        user_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: UUID | None = None,
        details: dict[str, JsonValue] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
    ) -> 'AuditLog':
        return cls(
            id=uuid4(),
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(UTC),
            success=success,
        )
