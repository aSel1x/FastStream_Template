from taskiq import TaskiqScheduler
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend, RedisScheduleSource

from app.core.config import Config


class TaskIqApp:
    def __init__(
            self,
            config: Config,
    ):
        self.__config = config
        self.broker = AioPikaBroker(
            config.rabbit.dsn.unicode_string(),
        )
        self.scheduler = TaskiqScheduler(
            self.broker, [RedisScheduleSource(config.redis.dsn.unicode_string())]
        )

    def initialize(self) -> 'TaskIqApp':
        self.broker.with_result_backend(RedisAsyncResultBackend(self.__config.redis.dsn.unicode_string()))
        return self
