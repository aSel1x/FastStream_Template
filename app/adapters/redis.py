"""
Redis Database
"""

from typing import Self

from pydantic import RedisDsn
from redis.asyncio import Redis

from app.utils.singleton import Singleton
from app.repositories import redis as repos


class RedisDB(metaclass=Singleton):
    def __init__(
            self,
            redis_dsn: RedisDsn,
            client: Redis | None = None
    ) -> None:
        self.__client = client
        self.__redis_dsn = redis_dsn

    async def __set_redis(self) -> None:
        if self.__client is None:
            self.__client = await Redis.from_url(
                self.__redis_dsn.unicode_string(), decode_responses=True
            )

    async def __set_repositories(self) -> None:
        if self.__client is not None:
            self.user = repos.UserRepo(self.__client)

    async def __aenter__(self) -> Self:
        await self.__set_redis()
        await self.__set_repositories()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
