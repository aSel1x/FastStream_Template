from dataclasses import dataclass
from os import getenv


@dataclass
class RabbitMQConfig:
    host: str = 'localhost'
    port: int = 5672
    user: str = 'guest'
    password: str = 'guest'  # noqa: S105 - RabbitMQ's documented default, overridden by env
    virtualhost: str = '/'

    @classmethod
    def from_environ(cls) -> RabbitMQConfig:
        return RabbitMQConfig(
            host=getenv('RABBITMQ_HOST', 'localhost'),
            port=int(getenv('RABBITMQ_PORT', '5672')),
            user=getenv('RABBITMQ_USER', 'guest'),
            password=getenv('RABBITMQ_PASSWORD', 'guest'),
            virtualhost=getenv('RABBITMQ_VIRTUALHOST', '/'),
        )

    @property
    def url(self) -> str:
        return f'amqp://{self.user}:{self.password}@{self.host}:{self.port}{self.virtualhost}'
