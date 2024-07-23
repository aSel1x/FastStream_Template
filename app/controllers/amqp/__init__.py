from faststream.rabbit import RabbitRouter

from .v1 import users
from .middlewares import (
    FastStreamExceptionHandler
)

router = RabbitRouter()
router.include_router(users.router)
router.add_middleware(FastStreamExceptionHandler)
