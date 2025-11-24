from datetime import UTC, datetime, timedelta
from typing import override

import jwt
from domain.user.exceptions import InvalidTokenError
from domain.user.interfaces import JWTInterface

from infrastructure.jwt.config import JWTConfig


class JWTService(JWTInterface):
    def __init__(self, config: JWTConfig) -> None:
        self.config: JWTConfig = config

    @override
    async def generate(self, payload: dict[str, str], exp: int) -> str:
        token_payload: dict[str, str | int] = {**payload}
        expire = datetime.now(UTC) + timedelta(seconds=exp)
        token_payload['exp'] = int(expire.timestamp())
        token_payload['iat'] = int(datetime.now(UTC).timestamp())

        encoded = jwt.encode(
            token_payload, self.config.secret_key, algorithm=self.config.algorithm
        )
        return encoded if isinstance(encoded, str) else encoded.decode('utf-8')

    @override
    async def extract(self, token: str) -> dict[str, str]:
        try:
            payload: dict[str, object] = jwt.decode(
                token, self.config.secret_key, algorithms=[self.config.algorithm]
            )
            result: dict[str, str] = {}

            for key in payload:
                if key not in ('exp', 'iat'):
                    value = payload[key]
                    result[key] = str(value) if value is not None else ''
            return result
        except jwt.ExpiredSignatureError as e:
            raise InvalidTokenError() from e
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError() from e

    @property
    @override
    def access_token_exp(self) -> int:
        return self.config.access_token_expire_seconds

    @property
    @override
    def refresh_token_exp(self) -> int:
        return self.config.refresh_token_expire_seconds
