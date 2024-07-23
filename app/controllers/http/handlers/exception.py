from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.exception.base import CustomException


def fastapi_exception_handler(_r: Request, exception: CustomException) -> JSONResponse:
    return JSONResponse(
        status_code=exception.http_code,
        content=dict(detail=exception.message)
    )
