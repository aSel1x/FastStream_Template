from .jwt import JWT
from .pwd import PWD

from ..config import Config


class Security:
    def __init__(self, config: Config):
        self.jwt = JWT(config.APP_SECRET_KEY)
        self.pwd = PWD()


__all__ = ['Security']
