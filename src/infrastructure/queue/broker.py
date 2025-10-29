from faststream.rabbit import RabbitBroker

from infrastructure.queue.config import RabbitMQConfig


def create_broker(config: RabbitMQConfig) -> RabbitBroker:
    return RabbitBroker(url=config.url)
