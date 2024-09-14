from asyncpg import exceptions as apg_exc
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import exc as sa_exc

from app.core.exception.base import CustomException


def custom_exc_handler(_r: Request, exception: CustomException) -> JSONResponse:
    return JSONResponse(
        status_code=exception.http_code,
        content=dict(detail=exception.message)
    )


def sql_exc_handler(_r: Request, exception: sa_exc.SQLAlchemyError | apg_exc.PostgresError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=dict(detail=repr(exception.with_traceback(None)))
    )


def exc_handler(_r: Request, exception: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=dict(detail=repr(exception.with_traceback(None)))
    )
