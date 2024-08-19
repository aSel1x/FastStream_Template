from .user import UserService
from .security import Security
from app.adapters import Database

from app.core.config import Config


class Services:
    def __init__(self, db: Database, config: Config):
        self.config = config
        self.db = db

        self.user = UserService(self)
        self.security = Security(config)


__all__ = ['Services']
