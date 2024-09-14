import asyncio
from typing import Annotated

from asyncpg import exceptions as apg_exc
from faststream import Context, ExceptionMiddleware
from faststream.rabbit.message import RabbitMessage
from loguru import logger
from sqlalchemy import exc as sa_exc

from app.core.exception.base import CustomException

exc_middleware = ExceptionMiddleware()


@exc_middleware.add_handler(CustomException)
async def custom_exc_handler(
        exc: CustomException,
        message: Annotated[RabbitMessage, Context()],
) -> None:
    logger.info(exc.with_traceback(None))
    await message.nack(requeue=False)


@exc_middleware.add_handler(sa_exc.SQLAlchemyError)
@exc_middleware.add_handler(apg_exc.PostgresError)
async def sa_exc_handler(
        exc: sa_exc.SQLAlchemyError | apg_exc.PostgresError,
        message: Annotated[RabbitMessage, Context()],
) -> None:
    logger.warning(exc.with_traceback(None))
    if isinstance(exc, (sa_exc.TimeoutError, apg_exc.TooManyConnectionsError)):
        await asyncio.sleep(60)
        await message.nack(requeue=True)
    else:
        await message.nack(requeue=False)


@exc_middleware.add_handler(Exception)
async def exc_handler(
        exc: Exception,
        message: Annotated[RabbitMessage, Context()],
) -> None:
    logger.warning(exc.with_traceback(None))
    await message.nack(requeue=False)
