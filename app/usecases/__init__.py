from .user import UserService
from .security import Security
from app.repositories import Repositories

from app.core.config import Config


class Services:
    def __init__(self, repositories: Repositories, config: Config):
        self.config = config
        self.repos = repositories

        self.user = UserService(self)
        self.security = Security(config)


__all__ = ['Services']
