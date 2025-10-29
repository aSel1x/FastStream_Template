from functools import partial

from domain.common.exception import BaseAppError
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.di import AppContainer
from infrastructure.jwt import JWTConfig
from infrastructure.mediator import register_event_handlers
from infrastructure.queue import RabbitMQConfig
from litestar import Litestar
from litestar.middleware import DefineMiddleware
from spritze import init

from presentation.api.controllers.user import UserController
from presentation.api.exception_handlers import app_exception_handler
from presentation.api.middleware import JWTAuthMiddleware


def get_litestar() -> Litestar:
    jwt_config = JWTConfig.from_environ()
    rabbitmq_config = RabbitMQConfig.from_environ()
    sqlalchemy_config = SQLAlchemyConfig.from_environ()

    container = AppContainer()
    container.context.update(
        JWTConfig=jwt_config,
        RabbitMQConfig=rabbitmq_config,
        SQLAlchemyConfig=sqlalchemy_config,
    )

    init(container)

    event_bus = container.event_bus()
    register_event_handlers(event_bus)

    jwt_service = container.jwt_service(jwt_config=jwt_config)

    app = Litestar(
        route_handlers=[UserController],
        exception_handlers={
            BaseAppError: app_exception_handler,
        },
        middleware=[
            DefineMiddleware(
                partial(JWTAuthMiddleware, jwt_service=jwt_service),
            )
        ],
        debug=True,
    )

    return app


app = get_litestar()
