"""One place that reads the environment, validated once at startup.

Configuration used to be eight independent `from_environ()` classmethods, each parsed wherever
it happened to be needed, each with its own defaults, and one of them swallowing its own
errors. A typo in a variable name surfaced as a confusing failure at first use — or as a
silently wrong default that nobody noticed.

`Settings.load()` is called at the top of the composition root, so a misconfigured service
fails at boot with a message naming the variable.
"""

import os
from dataclasses import dataclass
from typing import final

from application.common.exceptions import ConfigurationError
from infrastructure.cache.config import CacheConfig
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.email import EmailConfig
from infrastructure.hydra import HydraConfig
from infrastructure.observability.config import ObservabilityConfig
from infrastructure.queue import RabbitMQConfig
from infrastructure.secret_cipher import SECRET_ENCRYPTION_KEY_VAR
from infrastructure.security.rate_limiter import RateLimitConfig

MIN_SECRET_LENGTH = 32

_IN_MEMORY_CACHE_MESSAGE = (
    'CACHE_BACKEND must be "redis" outside development. The in-memory cache is per-process, '
    'which silently breaks pending 2FA challenges and introspection caching across replicas'
)
_IN_MEMORY_LIMITER_MESSAGE = (
    'RATE_LIMIT_BACKEND must be "redis" outside development. A per-process limiter multiplies '
    'every configured limit by the number of replicas'
)
PLACEHOLDER = 'change-me'


@final
@dataclass(frozen=True)
class Settings:
    environment: str
    app_secret_key: str
    secret_encryption_key: str
    database: SQLAlchemyConfig
    cache: CacheConfig
    rate_limit: RateLimitConfig
    hydra: HydraConfig
    rabbitmq: RabbitMQConfig
    email: EmailConfig
    observability: ObservabilityConfig

    @property
    def is_production(self) -> bool:
        """Fail closed: only an explicit `ENV=development` opts out of production behaviour.

        Debug tracebacks, permissive CORS and an auto-generated CSRF secret are all gated on
        this, so an unset or misspelled ENV must not be the permissive case.
        """
        return self.environment.lower() != 'development'

    @classmethod
    def load(cls) -> Settings:
        settings = cls(
            environment=os.getenv('ENV', 'production'),
            app_secret_key=os.getenv('APP_SECRET_KEY', ''),
            secret_encryption_key=os.getenv(SECRET_ENCRYPTION_KEY_VAR, ''),
            database=SQLAlchemyConfig.from_environ(),
            cache=CacheConfig.from_environ(),
            rate_limit=RateLimitConfig.from_environ(),
            hydra=HydraConfig.from_environ(),
            rabbitmq=RabbitMQConfig.from_environ(),
            email=EmailConfig.from_environ(),
            observability=ObservabilityConfig.from_environ(),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        """Refuse to start on a configuration that would only fail later, or fail silently."""
        if not self.is_production:
            return

        _require_secret('APP_SECRET_KEY', self.app_secret_key)
        _require_secret(SECRET_ENCRYPTION_KEY_VAR, self.secret_encryption_key)

        if not self.database.user or not self.database.password:
            _fail('POSTGRES_USER and POSTGRES_PASSWORD must be set')

        if self.cache.backend != 'redis':
            _fail(_IN_MEMORY_CACHE_MESSAGE)

        if self.rate_limit.backend != 'redis':
            _fail(_IN_MEMORY_LIMITER_MESSAGE)


def _require_secret(name: str, value: str) -> None:
    if not value:
        _fail(f'{name} must be set')
    if PLACEHOLDER in value:
        _fail(f'{name} is still the placeholder from .env.dist')
    if len(value) < MIN_SECRET_LENGTH:
        _fail(f'{name} must be at least {MIN_SECRET_LENGTH} characters')


def _fail(message: str) -> None:
    raise ConfigurationError(f'{message}. Generate secrets with: openssl rand -hex 32')
