from redis.asyncio import Redis

from app import models

from .base import Repository


class UserRepo(Repository[models.User]):
    def __init__(self, client: Redis):
        super().__init__(model=models.User, client=client)

    async def username_take(self, username: str) -> None:
        await self.client.sadd('taken_usernames', username)

    async def username_check(self, username: str) -> bool:
        return await self.client.sismember('taken_usernames', username)
