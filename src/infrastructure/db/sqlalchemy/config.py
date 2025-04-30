from dataclasses import dataclass
from os import getenv


@dataclass
class SQLAlchemyConfig:
    host: str = 'localhost'
    port: int = 5432
    database: str = 'test'
    user: str = ''
    password: str = ''
    echo: bool = True

    @property
    def full_url(self) -> str:
        return f'postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'

    @classmethod
    def from_environ(cls) -> 'SQLAlchemyConfig':
        return SQLAlchemyConfig(
            host=getenv('POSTGRES_HOST', 'localhost'),
            port=int(getenv('POSTGRES_PORT', 5432)),
            database=getenv('POSTGRES_DB', 'preprod'),
            user=getenv('POSTGRES_USER', ''),
            password=getenv('POSTGRES_PASSWORD', ''),
            echo=getenv('POSTGRES_ECHO', 'True').lower() == 'true',
        )
