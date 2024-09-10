from dishka import Provider, Scope, from_context, provide

from app.adapters import Adapters
from app.core.config import Config
from app.usecases import Services


class AppProvider(Provider):
    config = from_context(provides=Config, scope=Scope.APP)
    adapters = from_context(provides=Adapters, scope=Scope.APP)

    services = provide(
        Services,
        scope=Scope.REQUEST
    )
