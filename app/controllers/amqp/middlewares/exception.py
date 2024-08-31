from collections.abc import Awaitable, Callable
from typing import Any

from faststream import BaseMiddleware
from faststream.rabbit.annotations import RabbitMessage
from loguru import logger

from app.core.exception.base import CustomException


class FastStreamExceptionHandler(BaseMiddleware):
    async def consume_scope(self, call_next: Callable[[Any], Awaitable[Any]], msg: RabbitMessage) -> Any:
        try:
            return await call_next(msg)
        except CustomException as e:
            response = e.__dict__
        except Exception as e:
            logger.error(e)
            response = CustomException(
                internal_code=0,
                message=e.__str__()
            ).__dict__
        logger.error(response)
        await msg.nack(requeue=False)
        return response
