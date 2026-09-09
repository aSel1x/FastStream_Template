from dataclasses import dataclass
from os import getenv

from sqlalchemy import URL


@dataclass
class SQLAlchemyConfig:
    host: str = 'localhost'
    port: int = 5432
    database: str = 'test'
    user: str = ''
    password: str = ''
    # Off by default. `echo` logs every statement with its bound parameters — password hashes
    # and tokens included — so it has to be opted into, not remembered to be turned off.
    echo: bool = False
    pool_size: int = 10
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle_seconds: int = 1800
    statement_timeout_ms: int = 30_000
    application_name: str = 'backend-template'

    @property
    def url(self) -> URL:
        """Built with `URL.create`, which percent-encodes each component.

        Interpolating the password into an f-string corrupts the DSN as soon as it contains
        an `@`, `/`, `:` or any other reserved character.
        """
        return URL.create(
            drivername='postgresql+asyncpg',
            username=self.user,
            password=self.password,
            host=self.host,
            port=self.port,
            database=self.database,
        )

    @property
    def full_url(self) -> str:
        return self.url.render_as_string(hide_password=False)

    @classmethod
    def from_environ(cls) -> SQLAlchemyConfig:
        return SQLAlchemyConfig(
            host=getenv('POSTGRES_HOST', 'localhost'),
            port=int(getenv('POSTGRES_PORT', '5432')),
            database=getenv('POSTGRES_DB', 'preprod'),
            user=getenv('POSTGRES_USER', ''),
            password=getenv('POSTGRES_PASSWORD', ''),
            echo=getenv('POSTGRES_ECHO', 'false').lower() == 'true',
            pool_size=int(getenv('POSTGRES_POOL_SIZE', '10')),
            max_overflow=int(getenv('POSTGRES_MAX_OVERFLOW', '10')),
            pool_timeout=int(getenv('POSTGRES_POOL_TIMEOUT', '30')),
            pool_recycle_seconds=int(getenv('POSTGRES_POOL_RECYCLE_SECONDS', '1800')),
            statement_timeout_ms=int(getenv('POSTGRES_STATEMENT_TIMEOUT_MS', '30000')),
            application_name=getenv('POSTGRES_APPLICATION_NAME', 'backend-template'),
        )
