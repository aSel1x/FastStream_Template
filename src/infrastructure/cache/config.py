from dataclasses import dataclass
from os import getenv
from typing import Literal

from application.common.exceptions import ConfigurationError

CacheBackend = Literal['memory', 'redis']


@dataclass
class CacheConfig:
    backend: CacheBackend = 'memory'
    redis_url: str = 'redis://localhost:6379/0'

    @classmethod
    def from_environ(cls) -> CacheConfig:
        backend = getenv('CACHE_BACKEND', 'memory')
        if backend not in ('memory', 'redis'):
            raise ConfigurationError(f"CACHE_BACKEND must be 'memory' or 'redis', got {backend!r}")

        return cls(
            backend=backend,
            redis_url=getenv('REDIS_URL', 'redis://localhost:6379/0'),
        )
