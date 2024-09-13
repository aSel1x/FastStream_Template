from app.core.config import Config

from .jwt import JWT
from .pwd import PWD


class Security:
    def __init__(self, config: Config):
        self.jwt = JWT(config.app.secret)
        self.pwd = PWD()
