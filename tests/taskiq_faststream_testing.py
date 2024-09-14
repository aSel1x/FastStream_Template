import asyncio
import datetime as dt

from faststream.rabbit import RabbitBroker
from taskiq import ScheduledTask, ScheduleSource


class TestScheduleSource(ScheduleSource):
    def __init__(
            self,
            broker: RabbitBroker,
    ):
        self.__broker = broker

    async def startup(self) -> None:
        """Do something when starting broker."""
        return

    async def shutdown(self) -> None:
        """Do something on shutdown."""
        return

    async def get_schedules(self) -> list['ScheduledTask']:
        # Here you must return list of scheduled tasks from your source.
        return [
            ScheduledTask(
                task_name='',
                labels={},
                args=[],
                kwargs={},
                cron='* * * * *',
            ),
        ]

    # This method is optional. You may not implement this.
    # It's just a helper to people to be able to interact with your source.
    async def add_schedule(self, schedule: 'ScheduledTask') -> None:
        sleep_time = (schedule.time - dt.datetime.now(dt.timezone.utc)).total_seconds()
        entry, queue, exchange = map(schedule.kwargs.get, ('entity', 'queue', 'exchange'))
        await asyncio.sleep(sleep_time)
        await self.__broker.publish(entry, queue, exchange)

    # This method is completely optional, but if you want to support
    # schedule cancelation, you must implement it.
    async def delete_schedule(self, schedule_id: str) -> None:
        print('Deleting schedule:', schedule_id)

    # This method is optional. You may not implement this.
    # It's just a helper to people to be able to interact with your source.
    async def pre_send(self, task: 'ScheduledTask') -> None:
        """
        Actions to execute before task will be sent to broker.

        This method may raise ScheduledTaskCancelledError.
        This cancels the task execution.

        :param task: task that will be sent
        """

    # This method is optional. You may not implement this.
    # It's just a helper to people to be able to interact with your source.
    async def post_send(self, task: 'ScheduledTask') -> None:
        """
        Actions to execute after task was sent to broker.

        :param task: task that just have sent
        """
        return
