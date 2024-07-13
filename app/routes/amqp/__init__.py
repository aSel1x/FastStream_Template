from faststream.rabbit import RabbitRouter
from . import (
    users,
)

router = RabbitRouter()
router.include_router(users.router)
