from taskiq_faststream import StreamScheduler

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

    async def initialize(self) -> StreamScheduler:
        self.app.broker.include_router(amqp.router)
        return self.app.taskiq_scheduler
