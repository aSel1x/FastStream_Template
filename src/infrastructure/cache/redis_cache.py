from typing import final
import redis.asyncio as redis


@final
class RedisCache:
    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def get(self, key: str) -> str | None:
        value = await self._redis.get(key)
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else value

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        _ = await self._redis.set(key, value, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        _ = await self._redis.delete(key)
