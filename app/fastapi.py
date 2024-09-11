from fastapi import FastAPI

from app.controllers import http
from app.core.config import Config


class FastAPIApp:
    def __init__(
            self,
            config: Config,
    ):
        self.app = FastAPI(
            title=config.app.name,
            root_path=config.app.path,
            version=config.app.version,
            contact={
                'name': 'aSel1x',
                'url': 'https://asel1x.github.io',
                'email': 'asel1x@icloud.com',
            }
        )

    def initialize(self) -> 'FastAPIApp':
        http.setup_handlers(self.app)
        self.app.include_router(http.router)
        return self
