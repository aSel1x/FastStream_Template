from faststream import FastStream
from faststream.rabbit import RabbitBroker
from taskiq_faststream import AppWrapper, StreamScheduler
from taskiq.schedule_sources import LabelScheduleSource
from pydantic import AmqpDsn

from .config import Config
from app.controllers import amqp


def new_broker(amqp_dsn: AmqpDsn) -> RabbitBroker:
    return RabbitBroker(url=amqp_dsn.unicode_string())


class AMQP:
    def __init__(self, config: Config):
        self.config = config
        self.broker = self.setup_broker()
        self.faststream_app = FastStream(self.broker)
        self.taskiq_app = AppWrapper(self.faststream_app)
        self.taskiq_scheduler = StreamScheduler(
            self.taskiq_app, [LabelScheduleSource(self.taskiq_app)]
        )

    def setup_broker(self) -> RabbitBroker:
        broker = RabbitBroker(url=self.config.amqp_dsn.unicode_string())
        broker.include_router(amqp.router)
        return broker
