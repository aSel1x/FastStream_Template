from .user import UserService
from .security import Security
from app.adapters import Adapters

from app.core.config import Config


class Services:
    def __init__(self, adapters: Adapters, config: Config):
        self.config = config
        self.adapters = adapters

        self.user = UserService(self)
        self.security = Security(config)


__all__ = ['Services']
