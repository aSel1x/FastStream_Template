import datetime as dt
from typing import Any, Self

from faststream import FastStream
from faststream.rabbit import RabbitBroker
from pydantic import AmqpDsn
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_faststream import AppWrapper, StreamScheduler
from taskiq_faststream.types import ScheduledTask


class AmqpQueue:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
            self,
            amqp_dsn: AmqpDsn,
            broker: RabbitBroker | None = None,
            faststream_app: FastStream | None = None,
            taskiq_app: AppWrapper | None = None,
            scheduler: StreamScheduler | None = None
    ) -> None:
        if not hasattr(self, 'initialized'):
            self.__amqp_dsn = amqp_dsn
            self.broker = broker
            self.faststream_app = faststream_app
            self.__taskiq_app = taskiq_app
            self.taskiq_scheduler = scheduler
            self.initialized = True

    async def create_task(
            self,
            entry: Any,
            queue: str,
            *,
            exchange: str | None = None,
            when: dt.datetime | int | None = None,
    ) -> None:
        if when is None:
            await self.broker.publish(entry, queue, exchange)
        elif isinstance(when, dt.datetime):
            pass
        elif isinstance(when, int):
            when = dt.datetime.now() + dt.timedelta(seconds=when)
        else:
            raise ValueError

        self.__taskiq_app.task(
            entry,
            queue=queue,
            exchange=exchange,
            schedule=[ScheduledTask(time=when)]
        )

    async def __set_broker(self) -> None:
        if self.broker is None:
            self.broker = RabbitBroker(self.__amqp_dsn.unicode_string())

    async def __set_faststream_app(self) -> None:
        if self.faststream_app is None:
            self.faststream_app = FastStream(self.broker)

    async def __set_taskiq_app(self) -> None:
        if self.__taskiq_app is None:
            self.__taskiq_app = AppWrapper(self.faststream_app)

    async def __set_taskiq_scheduler(self) -> None:
        if self.taskiq_scheduler is None:
            self.taskiq_scheduler = StreamScheduler(
                self.__taskiq_app, [LabelScheduleSource(self.__taskiq_app)]
            )

    async def __aenter__(self) -> Self:
        await self.__set_broker()
        await self.__set_faststream_app()
        await self.__set_taskiq_app()
        await self.__set_taskiq_scheduler()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        pass
