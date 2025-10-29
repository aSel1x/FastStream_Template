from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
from domain.user.exceptions import InvalidTokenError


class JWTService:
    _secret_key: str
    _algorithm: str

    def __init__(self, secret_key: str, algorithm: str = 'HS256') -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm

    async def generate(self, payload: dict[str, str], exp: int) -> str:
        token_payload: dict[str, str | int] = {**payload}
        expire = datetime.now(UTC) + timedelta(seconds=exp)
        token_payload['exp'] = int(expire.timestamp())
        token_payload['iat'] = int(datetime.now(UTC).timestamp())

        encoded = jwt.encode(token_payload, self._secret_key, algorithm=self._algorithm)
        return encoded if isinstance(encoded, str) else encoded.decode('utf-8')

    async def extract(self, token: str) -> dict[str, str]:
        try:
            payload: dict[str, object] = jwt.decode(
                token, self._secret_key, algorithms=[self._algorithm]
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
