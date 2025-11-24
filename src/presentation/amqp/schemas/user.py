from pydantic import BaseModel

from presentation.amqp.schemas.base import event


@event
class UserCreatedEventSchema(BaseModel):
    user_id: str
    username: str
    email: str | None = None


@event
class UserAuthenticatedEventSchema(BaseModel):
    user_id: str
    username: str


@event
class UserProfileUpdatedEventSchema(BaseModel):
    user_id: str
    updated_fields: str


@event
class UserDeletedEventSchema(BaseModel):
    user_id: str
