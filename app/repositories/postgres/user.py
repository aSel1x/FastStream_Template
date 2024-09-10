from sqlalchemy.ext.asyncio import async_sessionmaker

from app import models

from .base import Repository


class UserRepo(Repository[models.User]):
    def __init__(self, session_maker: async_sessionmaker):
        super().__init__(model=models.User, session_maker=session_maker)

    async def retrieve_by_username(self, username: str) -> models.User | None:
        return await self.retrieve_one(
            where_clauses=[self.model.username == username]
        )
