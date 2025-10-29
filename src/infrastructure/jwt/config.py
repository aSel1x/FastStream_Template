from dataclasses import dataclass
from os import getenv


@dataclass
class JWTConfig:
    secret_key: str
    algorithm: str = 'HS256'
    access_token_expire_seconds: int = 60 * 15  # 15 minutes
    refresh_token_expire_seconds: int = 60 * 60 * 24 * 7  # 7 days

    @classmethod
    def from_environ(cls) -> 'JWTConfig':
        return JWTConfig(
            secret_key=getenv(
                'JWT_SECRET_KEY', 'super-secret-key-change-in-production'
            ),
            algorithm=getenv('JWT_ALGORITHM', 'HS256'),
            access_token_expire_seconds=int(
                getenv('JWT_ACCESS_TOKEN_EXPIRE_SECONDS', str(60 * 15))
            ),
            refresh_token_expire_seconds=int(
                getenv('JWT_REFRESH_TOKEN_EXPIRE_SECONDS', str(60 * 60 * 24 * 7))
            ),
        )
