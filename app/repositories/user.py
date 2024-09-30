from sqlmodel.ext.asyncio.session import AsyncSession

from .. import models
from .base import Repository


class UserRepository(Repository[models.User]):
    def __init__(self, session: AsyncSession):
        super().__init__(model=models.User, session=session)

    async def retrieve_by_username(self, username: str) -> models.User | None:
        return await self.retrieve_one(
            where_clauses=[self.model.username == username]
        )
