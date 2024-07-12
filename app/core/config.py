from pydantic import AmqpDsn, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', case_sensitive=True
    )

    # APP
    APP_PATH: str
    APP_TITLE: str
    APP_VERSION: str
    APP_SECRET_KEY: str

    # DATABASE
    POSTGRES_HOST: str = 'localhost'
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = 'postgres'
    POSTGRES_PASSWORD: str = 'postgres'
    POSTGRES_DB: str = 'postgres'

    # RabbitMQ
    AMQP_USERNAME: str
    AMQP_PASSWORD: str
    AMQP_HOST: str
    AMQP_PORT: int

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
