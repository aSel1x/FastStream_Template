from fastapi import FastAPI, APIRouter

from .v1 import user
from .handlers import (
    fastapi_exception_handler
)
from ...core.exception.base import CustomException


def setup(_app: FastAPI):
    _app.add_exception_handler(CustomException, fastapi_exception_handler)


router = APIRouter(prefix='/v1')
router.include_router(user.router)
