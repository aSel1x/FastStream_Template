from faststream.rabbit import RabbitRouter

from . import taskiq
from .v1 import user
from .middlewares import (
    FastStreamExceptionHandler
)

router = RabbitRouter()
router.include_router(taskiq.router)
router.include_router(user.router)
router.add_middleware(FastStreamExceptionHandler)
