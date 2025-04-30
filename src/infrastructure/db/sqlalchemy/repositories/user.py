from uuid import UUID

from application.user import dto
from domain.user import entities
from domain.user.interfaces import UserRepositoryInterface
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import exists, select

from infrastructure.db.sqlalchemy.models.user import UserModel
from infrastructure.db.sqlalchemy.repositories.base import SQLAlchemyRepo


class SQLAlchemyUserRepo(SQLAlchemyRepo, UserRepositoryInterface):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def acquire_by_uuid(self, user_uuid: UUID) -> dto.UserDTO:
        user: entities.User | None = await self._session.get(entities.User, user_uuid)
        return user

    async def add(self, user: entities.User) -> None:
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)

    async def check_username_exists(self, username: str) -> bool:
        result: bool | None = await self._session.scalar(
            select(exists().where(UserModel.username == username))
        )
        return result or False
