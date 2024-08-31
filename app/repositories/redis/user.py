from redis.asyncio import Redis

from app import models

from .base import Repository


class UserRepo(Repository[models.User]):
    def __init__(self, client: Redis):
        super().__init__(model=models.User, client=client)
