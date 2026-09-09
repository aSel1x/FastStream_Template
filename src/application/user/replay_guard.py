"""Stops a one-time code from being accepted twice.

A TOTP code stays valid for its whole time step (and, with a tolerance window, the adjacent
ones). Verifying it does not consume it, so a code observed in transit can be replayed for
tens of seconds. Recording each accepted code for the length of that window closes it.
"""

import hashlib
from typing import final
from uuid import UUID

from application.common.interfaces.system.cache import CacheInterface

#: One TOTP step plus the tolerance window on either side, with margin.
CODE_MEMORY_SECONDS = 120


@final
class UsedCodeRegistry:
    def __init__(self, cache: CacheInterface) -> None:
        self._cache = cache

    def _key(self, user_id: UUID, code: str) -> str:
        # Hashed: the cache should not hold a credential in readable form, even briefly.
        digest = hashlib.sha256(f'{user_id}:{code}'.encode()).hexdigest()
        return f'used_2fa_code:{digest}'

    async def was_used(self, user_id: UUID, code: str) -> bool:
        return await self._cache.get(self._key(user_id, code)) is not None

    async def remember(self, user_id: UUID, code: str) -> None:
        await self._cache.set(self._key(user_id, code), '1', ttl_seconds=CODE_MEMORY_SECONDS)
