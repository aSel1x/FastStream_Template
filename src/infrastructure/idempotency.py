from typing import final

from pydantic import JsonValue, TypeAdapter

from application.common.interfaces.system.cache import CacheInterface

_IDEMPOTENCY_TTL_SECONDS = 86400

_response_adapter = TypeAdapter[dict[str, JsonValue]](dict[str, JsonValue])


def _cache_key(endpoint: str, scope: str, idempotency_key: str) -> str:
    return f'idempotency:{endpoint}:{scope}:{idempotency_key}'


@final
class IdempotencyStore:
    """Replays a cached JSON response for a repeated (endpoint, scope, Idempotency-Key).

    `scope` is any caller-chosen string that keeps one client's Idempotency-Key values from
    colliding with another's (e.g. the requesting IP). Lets clients safely retry a POST after
    a network timeout without risking duplicate side effects (e.g. a second account created
    from a retried registration).
    """

    def __init__(self, cache: CacheInterface) -> None:
        self._cache = cache

    async def get_cached_response(
        self,
        endpoint: str,
        scope: str,
        idempotency_key: str,
    ) -> dict[str, JsonValue] | None:
        cached = await self._cache.get(_cache_key(endpoint, scope, idempotency_key))
        if cached is None:
            return None
        return _response_adapter.validate_json(cached)

    async def cache_response(
        self,
        endpoint: str,
        scope: str,
        idempotency_key: str,
        response: dict[str, JsonValue],
    ) -> None:
        key = _cache_key(endpoint, scope, idempotency_key)
        await self._cache.set(
            key,
            _response_adapter.dump_json(response).decode(),
            ttl_seconds=_IDEMPOTENCY_TTL_SECONDS,
        )
