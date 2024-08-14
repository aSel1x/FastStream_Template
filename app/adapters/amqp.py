import datetime as dt
from typing import Any

from faststream import FastStream
from faststream.rabbit import RabbitBroker
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_faststream import AppWrapper, StreamScheduler
from taskiq_faststream.types import ScheduledTask


class AppAMQP:
    def __init__(self, broker: RabbitBroker):
        self.broker = broker
        self.faststream_app = FastStream(self.broker)
        self.taskiq_app = AppWrapper(self.faststream_app)
        self.taskiq_scheduler = StreamScheduler(self.taskiq_app, [LabelScheduleSource(self.taskiq_app)])

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

        self.taskiq_app.task(
            entry,
            queue=queue,
            exchange=exchange,
            schedule=[ScheduledTask(time=when)]
        )
