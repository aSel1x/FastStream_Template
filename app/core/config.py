from pydantic import AmqpDsn, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', case_sensitive=True
    )

    # APP
    APP_PATH: str = '/api'
    APP_TITLE: str = 'Template'
    APP_VERSION: str = '1.0.0'
    APP_SECRET_KEY: str = '123abc'

    # DATABASE
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = 'postgres'
    POSTGRES_PASSWORD: str = 'postgres'
    POSTGRES_DB: str = 'postgres'

    # RabbitMQ
    AMQP_HOST: str = 'localhost'
    AMQP_PORT: int = 5672
    AMQP_USERNAME: str = 'guest'
    AMQP_PASSWORD: str = None

    # Redis
    REDIS_HOST: str = 'localhost'
    REDIS_PORT: int = 6379
    REDIS_SSL: bool = False
    REDIS_USERNAME: str = None
    REDIS_PASSWORD: str = None

    @property
    def pg_dsn(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme='postgresql+asyncpg',
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    @property
    def amqp_dsn(self) -> AmqpDsn:
        return AmqpDsn.build(
            scheme='amqp',
            username=self.AMQP_USERNAME,
            password=self.AMQP_PASSWORD,
            host=self.AMQP_HOST,
            port=self.AMQP_PORT
        )

    @property
    def redis_dsn(self) -> RedisDsn:
        return RedisDsn.build(
            scheme='rediss' if self.REDIS_SSL else 'redis',
            username=self.REDIS_USERNAME,
            password=self.REDIS_PASSWORD,
            host=self.REDIS_HOST,
            port=self.REDIS_PORT
        )
