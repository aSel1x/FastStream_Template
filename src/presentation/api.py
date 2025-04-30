from dishka import make_async_container
from dishka.integrations import litestar as litestar_integration
from dotenv import load_dotenv
from infrastructure.db.sqlalchemy.config import SQLAlchemyConfig
from infrastructure.ioc import DiProvider
from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin

from presentation.controllers.api import UserController

load_dotenv()

container = make_async_container(
    DiProvider(), context={SQLAlchemyConfig: SQLAlchemyConfig.from_environ()}
)


def get_litestar() -> Litestar:
    """
    Create and return a Litestar application instance.
    """
    app = Litestar(
        debug=True,
        route_handlers=[UserController],
        openapi_config=OpenAPIConfig(
            title='Litestar Example',
            description='Example of litestar',
            version='0.0.1',
            render_plugins=[SwaggerRenderPlugin()],
        ),
    )
    litestar_integration.setup_dishka(container=container, app=app)
    return app
