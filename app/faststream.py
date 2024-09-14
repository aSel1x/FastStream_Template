from faststream import FastStream
from faststream.rabbit import RabbitBroker

from app.controllers import amqp
from app.core.config import Config


class FastStreamApp:
    def __init__(
            self,
            config: Config,
    ):
        self.broker = RabbitBroker(config.rabbit.dsn.unicode_string())
        self.app = FastStream(self.broker)

    def initialize(self) -> 'FastStreamApp':
        amqp.setup_middlewares(self.app)
        self.broker.include_router(amqp.router)
        return self
