from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from .base import IDModel, TimestampModel


class UserBase(SQLModel):
    username: str = Field(index=True)
    is_active: bool = True


class UserCreate(SQLModel):
    username: str
    password: str

    def __str__(self):
        return self.username


class User(UserBase, IDModel, TimestampModel, table=True):  # type: ignore
    password: str


class UserAuth(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
