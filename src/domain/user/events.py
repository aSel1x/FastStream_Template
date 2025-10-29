from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from domain.common.event import BaseEvent


@dataclass
class UserCreatedEvent(BaseEvent):
    user_id: UUID
    username: str
    email: str | None


@dataclass
class UserAuthenticatedEvent(BaseEvent):
    user_id: UUID
    username: str


@dataclass
class UserProfileUpdatedEvent(BaseEvent):
    user_id: UUID
    updated_fields: tuple[str, ...]


@dataclass
class UserDeletedEvent(BaseEvent):
    user_id: UUID
