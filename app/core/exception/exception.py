from typing import Any, Awaitable, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from faststream import BaseMiddleware
from faststream.rabbit.message import RabbitMessage
from loguru import logger

from .status import HTTPStatus


class AppException(Exception):
    def __init__(self, status_code: int, detail: str | None):
        self.status_code = status_code
        self.detail = detail or HTTPStatus(status_code).phrase  # type: ignore

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code}, detail={self.detail})"


def fastapi_exception_handler(_r: Request, exception: AppException):
    return JSONResponse(
        status_code=exception.status_code,
        content=dict(detail=exception.detail)
    )


class FastStreamExceptionHandler(BaseMiddleware):
    async def consume_scope(
            self,
            call_next: Callable[[Any], Awaitable[Any]],
            msg: RabbitMessage,
    ) -> Any:
        try:
            return await call_next(msg)
        except AppException as e:
            response = e.__dict__
        except Exception as e:
            response = AppException(
                status_code=500,
                detail=e.__str__()
            ).__dict__

        logger.error(response)
        await msg.nack(requeue=False)
        return response
