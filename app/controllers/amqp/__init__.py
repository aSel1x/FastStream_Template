from faststream.rabbit import RabbitRouter

from .v1 import user
from .middlewares import (
    FastStreamExceptionHandler
)

router = RabbitRouter()
router.include_router(user.router)
router.add_middleware(FastStreamExceptionHandler)
