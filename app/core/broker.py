from abc import ABC, abstractmethod
from typing import Self

from faststream.rabbit import RabbitBroker as FastStreamRabbitBroker

from app.controllers import amqp


class AbstractBroker(ABC):

    @abstractmethod
    async def publish(self, *args, **kwargs):
        ...

    @abstractmethod
    def custom_setup(self) -> Self:
        ...


class RabbitBroker(FastStreamRabbitBroker, AbstractBroker):
    def __init__(self, dsn: str):
        super().__init__(url=dsn)

    def custom_setup(self) -> 'RabbitBroker':
        self.include_router(amqp.router)
        return self
