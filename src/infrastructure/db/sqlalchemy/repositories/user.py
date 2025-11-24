from typing import override

from domain.user import entities
from domain.user.interfaces import UserRepositoryInterface
from domain.user.value_objects import Email, UserID, Username
from infrastructure.db.sqlalchemy.models.user import USERS_TABLE
from infrastructure.db.sqlalchemy.repositories.base import SQLAlchemyRepo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists, select


class SQLAlchemyUserRepo(SQLAlchemyRepo, UserRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    @override
    async def acquire_by_id(self, user_id: UserID) -> entities.User | None:
        user: entities.User | None = await self._session.get(
            entities.User, user_id.to_raw()
        )
        return user

    @override
    async def acquire_by_username(self, username: Username) -> entities.User | None:
        user: entities.User | None = await self._session.scalar(
            select(entities.User).where(USERS_TABLE.c.username == username.to_raw())
        )
        return user

    @override
    async def acquire_by_email(self, email: Email) -> entities.User | None:
        if email.to_raw() is None:
            return None
        user: entities.User | None = await self._session.scalar(
            select(entities.User).where(USERS_TABLE.c.email == email.to_raw())
        )
        return user

    @override
    async def add(self, user: entities.User) -> None:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)

    @override
    async def update(self, user: entities.User) -> None:
        _ = await self._session.merge(user)
        await self._session.flush()
        await self._session.refresh(user)

    @override
    async def check_username_exists(self, username: Username) -> bool:
        result: bool | None = await self._session.scalar(
            select(exists().where(USERS_TABLE.c.username == username.to_raw()))
        )
        return result or False

    @override
    async def check_email_exists(self, email: Email) -> bool:
        if email.to_raw() is None:
            return False
        result: bool | None = await self._session.scalar(
            select(exists().where(USERS_TABLE.c.email == email.to_raw()))
        )
        return result or False
