from fastapi import FastAPI, APIRouter

from asyncpg.exceptions import PostgresError
from sqlalchemy.exc import SQLAlchemyError

from .v1 import user
from . import handlers
from app.core.exception.base import CustomException


def setup_handlers(_app: FastAPI):
    _app.add_exception_handler(CustomException, handlers.custom_exc_handler)
    _app.add_exception_handler(SQLAlchemyError, handlers.sql_exc_handler)
    _app.add_exception_handler(PostgresError, handlers.sql_exc_handler)
    _app.add_exception_handler(Exception, handlers.exc_handler)


router = APIRouter(prefix='/v1')
router.include_router(user.router)
