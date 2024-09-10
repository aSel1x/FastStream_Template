from app.adapters.rabbitmq import AmqpQueue
from app.controllers import amqp
from app.core.config import Config


class FastStreamApp:
    def __init__(
            self,
            config: Config,
            adapter_amqp: AmqpQueue
    ):
        self.app = adapter_amqp

    async def initialize(self) -> 'FastStreamApp':
        self.app.broker.include_router(amqp.router)
        return self
