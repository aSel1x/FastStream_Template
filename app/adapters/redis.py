"""
Redis Database
"""

from typing import Self

from pydantic import RedisDsn
from redis.asyncio import Redis

from app.repositories import redis as repos


class RedisDB:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
            self,
            redis_dsn: RedisDsn,
            client: Redis | None = None
    ) -> None:
        if not hasattr(self, 'initialized'):
            self.__client = client
            self.__redis_dsn = redis_dsn
            self.__initialized = True

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

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        pass
