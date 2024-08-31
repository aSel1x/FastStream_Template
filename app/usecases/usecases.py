from app.adapters import Adapters
from app.core.config import Config

from .security import Security
from .user import UserService


class Services:
    def __init__(self, adapters: Adapters, config: Config):
        self.config = config
        self.adapters = adapters

        self.user = UserService(self)
        self.security = Security(config)


__all__ = ['Services']
