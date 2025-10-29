from __future__ import annotations

from pydantic import BaseModel


class EventData(BaseModel):
    event_type: str
    event_id: str
    event_timestamp: int


class UserCreatedData(BaseModel):
    user_id: str
    username: str
    email: str | None = None


class UserCreatedEventSchema(EventData):
    data: UserCreatedData


class UserAuthenticatedData(BaseModel):
    user_id: str
    username: str


class UserAuthenticatedEventSchema(EventData):
    data: UserAuthenticatedData


class UserProfileUpdatedData(BaseModel):
    user_id: str
    updated_fields: str


class UserProfileUpdatedEventSchema(EventData):
    data: UserProfileUpdatedData


class UserDeletedData(BaseModel):
    user_id: str


class UserDeletedEventSchema(EventData):
    data: UserDeletedData
