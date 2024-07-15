from fastapi import Request
from fastapi.responses import JSONResponse

from .status import HTTPStatus


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str | None):
        self.status_code = status_code
        self.detail = detail or HTTPStatus(status_code).phrase  # type: ignore


def fastapi_exception_handler(_r: Request, exception: HTTPException):
    return JSONResponse(
        status_code=exception.status_code,
        content=dict(detail=exception.detail)
    )
