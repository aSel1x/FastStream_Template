import datetime as dt
from typing import Any, Self

from aio_pika import RobustConnection
from faststream import FastStream
from faststream.rabbit import RabbitBroker
from pydantic import AmqpDsn, RedisDsn
from taskiq import ScheduledTask, TaskiqScheduler
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisScheduleSource

from app.utils.singleton import Singleton


class RabbitQueue(metaclass=Singleton):
    def __init__(
        self,
        rabbit_dsn: AmqpDsn,
        redis_dsn: RedisDsn,
        faststream_broker: RabbitBroker | None = None,
        faststream_broker_connect: RobustConnection | None = None,
        faststream_app: FastStream | None = None,
        taskiq_broker: AioPikaBroker | None = None,
        taskiq_scheduler_source: RedisScheduleSource | None = None,
        taskiq_scheduler: TaskiqScheduler | None = None,
    ) -> None:
        self.__rabbit_dsn = rabbit_dsn
        self.__redis_dsn = redis_dsn
        self.__faststream_broker = faststream_broker
        self.__faststream_broker_connect = faststream_broker_connect
        self.__faststream_app = faststream_app
        self.__taskiq_broker = taskiq_broker
        self.__taskiq_scheduler_source = taskiq_scheduler_source
        self.__taskiq_scheduler = taskiq_scheduler

    async def create_task(
        self,
        entry: Any,
        queue: str,
        *,
        exchange: str | None = None,
        when: dt.datetime | int | None = None,
    ) -> None:

        if when is None:
            if self.__faststream_broker is not None:
                await self.__set_faststream_broker_connect()
                await self.__faststream_broker.publish(entry, queue, exchange)
            return
        elif isinstance(when, dt.datetime):
            pass
        elif isinstance(when, int):
            when = dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=when)
        else:
            raise ValueError(
                "{hen=} must be {type(dt.datetime)} | {type(int)} | {type(None)}"
            )

        if self.__taskiq_scheduler_source is not None:
            await self.__taskiq_scheduler_source.add_schedule(
                ScheduledTask(
                    task_name=f"{exchange}:{queue}:{entry}",
                    args=[],
                    kwargs={
                        "entity": entry,
                        "queue": queue,
                        "exchange": exchange,
                    },
                    labels={},
                    time=when,
                )
            )

    async def __set_faststream_broker(self) -> None:
        if self.__faststream_broker is None:
            self.__faststream_broker = RabbitBroker(self.__rabbit_dsn.unicode_string())

    async def __set_faststream_broker_connect(self) -> None:
        if self.__faststream_broker and self.__faststream_broker_connect is None:
            self.__faststream_broker_connect = await self.__faststream_broker.connect()
        elif (
            self.__faststream_broker_connect
            and self.__faststream_broker_connect.is_closed
        ):
            await self.__faststream_broker_connect.reconnect()

    async def __set_faststream_app(self) -> None:
        if self.__faststream_app is None:
            self.__faststream_app = FastStream(self.__faststream_broker)

    async def __set_taskiq_app(self) -> None:
        if self.__taskiq_broker is None:
            self.__taskiq_broker = AioPikaBroker(self.__rabbit_dsn.unicode_string())

    async def __set_taskiq_scheduler_source(self) -> None:
        if self.__taskiq_scheduler_source is None:
            self.__taskiq_scheduler_source = RedisScheduleSource(
                self.__redis_dsn.unicode_string()
            )

    async def __set_taskiq_scheduler(self) -> None:
        if (
            self.__taskiq_scheduler is None
            and self.__taskiq_broker
            and self.__taskiq_scheduler_source
        ):
            self.__taskiq_scheduler = TaskiqScheduler(
                self.__taskiq_broker, [self.__taskiq_scheduler_source]
            )

    async def __aenter__(self) -> Self:
        await self.__set_faststream_broker()
        await self.__set_faststream_app()
        await self.__set_taskiq_app()
        await self.__set_taskiq_scheduler_source()
        await self.__set_taskiq_scheduler()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
