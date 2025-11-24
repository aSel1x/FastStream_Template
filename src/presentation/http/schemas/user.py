from pydantic import BaseModel


class UserProfileUpdatedRequestSchema(BaseModel):
    username: str | None = None
    email: str | None = None
