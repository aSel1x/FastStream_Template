from typing import final
from litestar.config.cors import CORSConfig


class AppCORSConfig:
    @classmethod
    def default(cls) -> CORSConfig:
        return CORSConfig(
            allow_origins=["http://localhost:3000", "http://localhost:8080"],
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True,
            max_age=3600,
        )

    @classmethod
    def production(cls, allowed_origins: list[str] | None = None) -> CORSConfig:
        if not allowed_origins:
            raise ValueError(
                'ALLOWED_ORIGINS must be set to a comma-separated list of origins in production'
            )
        return CORSConfig(
            allow_origins=allowed_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            allow_credentials=True,
            max_age=3600,
        )


@final
class CORSMiddleware:
    def __init__(self, config: CORSConfig | None = None) -> None:
        self._config = config or AppCORSConfig.default()

    @property
    def config(self) -> CORSConfig:
        return self._config