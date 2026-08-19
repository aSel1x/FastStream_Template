from datetime import UTC, datetime, timedelta


class InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[str, datetime | None]] = {}

    async def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if entry is None:
            return None

        value, expires_at = entry
        if expires_at is not None and datetime.now(UTC) >= expires_at:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        _ = self._store.pop(key, None)
