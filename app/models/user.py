from sqlmodel import SQLModel

from .base import IDModel, TimestampModel


class UserBase(SQLModel):
    username: str
    is_active: bool = True


class UserCreate(SQLModel):
    username: str
    password: str

    def __str__(self):
        return self.username


class UserAuth(SQLModel):
    token: str


class User(UserBase, IDModel, TimestampModel, table=True):  # type: ignore
    password: str
