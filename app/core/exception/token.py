from .base import (
    UnauthorizedException,
)


class TokenInvalid(UnauthorizedException):
    def __init__(self):
        super().__init__('Invalid token.')


class TokenExpired(UnauthorizedException):
    def __init__(self):
        super().__init__('Token expired.')
