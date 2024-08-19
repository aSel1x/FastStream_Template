from fastapi import FastAPI, APIRouter

from .v1 import user
from .handlers import (
    fastapi_exception_handler
)
from app.core.exception.base import CustomException


def setup_handlers(_app: FastAPI):
    _app.add_exception_handler(CustomException, fastapi_exception_handler)


router = APIRouter(prefix='/v1')
router.include_router(user.router)
