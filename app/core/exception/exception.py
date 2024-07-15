from typing import Callable, Any, Awaitable

from fastapi import Request
from fastapi.responses import JSONResponse

from faststream import BaseMiddleware
from faststream.rabbit.message import RabbitMessage

from .status import HTTPStatus


class AppException(Exception):
    def __init__(self, status_code: int, detail: str | None):
        self.status_code = status_code
        self.detail = detail or HTTPStatus(status_code).phrase  # type: ignore


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
            response = await call_next(msg)
        except AppException as e:
            response = dict(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            response = dict(status_code=500, content={"detail": e.__str__()})
        await msg.nack(requeue=False)
        return response
