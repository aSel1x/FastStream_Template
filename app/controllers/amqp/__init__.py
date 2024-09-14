from faststream import FastStream
from faststream.rabbit import RabbitRouter

from .v1 import user
from . import taskiq
from . import middlewares


def setup_middlewares(_app: FastStream):
    _app.broker.add_middleware(middlewares.exc_middleware)


router = RabbitRouter()
router.include_router(taskiq.router)
router.include_router(user.router)
