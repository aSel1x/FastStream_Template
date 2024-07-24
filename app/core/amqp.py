from faststream import FastStream
from faststream.broker.core.usecase import BrokerUsecase
from taskiq_faststream import AppWrapper, StreamScheduler
from taskiq.schedule_sources import LabelScheduleSource

from .broker import RabbitBroker


def get_faststream_app(broker: BrokerUsecase) -> FastStream:
    return FastStream(broker)


def get_taskiq_app(faststream_app: FastStream) -> AppWrapper:
    return AppWrapper(faststream_app)


def get_taskiq_scheduler(taskiq_app: AppWrapper) -> StreamScheduler:
    return StreamScheduler(taskiq_app, [LabelScheduleSource(taskiq_app)])


class AppAMQP:
    def __init__(self, broker: RabbitBroker):
        self.broker = broker
        self.faststream_app = get_faststream_app(self.broker)
        self.taskiq_app = get_taskiq_app(self.faststream_app)
        self.taskiq_scheduler = get_taskiq_scheduler(self.taskiq_app)
