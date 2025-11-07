from domain.common.exception import BaseAppError
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.di import AppContainer
from infrastructure.jwt import JWTConfig
from infrastructure.mediator import EventBus, register_event_handlers
from infrastructure.queue import RabbitMQConfig
from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig
from spritze import init, resolve

from presentation.api.controllers.user import UserController
from presentation.api.exception_handlers import app_exception_handler
from presentation.api.security import create_jwt_auth


def get_litestar() -> Litestar:
    jwt_config = JWTConfig.from_environ()
    rabbitmq_config = RabbitMQConfig.from_environ()
    sqlalchemy_config = SQLAlchemyConfig.from_environ()

    init(
        AppContainer(),
        context={
            JWTConfig: jwt_config,
            RabbitMQConfig: rabbitmq_config,
            SQLAlchemyConfig: sqlalchemy_config,
        },
    )

    event_bus = resolve(EventBus)
    register_event_handlers(event_bus)

    jwt_auth = create_jwt_auth(token_secret=jwt_config.secret_key)

    openapi_config = OpenAPIConfig(
        title='FastStream API',
        version='1.0.0',
    )

    app = Litestar(
        route_handlers=[UserController],
        exception_handlers={
            BaseAppError: app_exception_handler,
        },
        on_app_init=[jwt_auth.on_app_init],
        debug=True,
        openapi_config=openapi_config,
    )

    return app


app = get_litestar()
