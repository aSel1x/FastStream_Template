import jwt

from app.core import exception


class JWT:
    def __init__(self, secret_key: str):
        self.secret_key: str = secret_key

    def decode(self, token: str) -> dict | None:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
        except jwt.exceptions.ExpiredSignatureError:
            raise exception.token.TokenExpired
        except jwt.exceptions.PyJWTError:
            raise exception.token.TokenInvalid
        return payload

    def encode(self, payload: dict, expire_at: int | float | None = None) -> str:
        if expire_at:
            payload['exp'] = expire_at
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
