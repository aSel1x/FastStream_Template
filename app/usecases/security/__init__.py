from .jwt import JWT
from .pwd import PWD

from app.core.config import Config


class Security:
    def __init__(self, config: Config):
        self.jwt = JWT(config.app.secret)
        self.pwd = PWD()


__all__ = ['Security']
