from dishka import Provider, Scope, from_context, provide

from app.adapters import Adapters
from app.core.config import Config
from app.usecases import Services


class AppProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)

    @provide(scope=Scope.APP)
    async def get_adapters(self, config: Config) -> Adapters:
        async with Adapters.create(config) as adapters:
            return adapters

    services = provide(
        Services,
        scope=Scope.REQUEST
    )
