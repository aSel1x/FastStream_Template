from .base import UnauthorizedException


class TokenInvalid(UnauthorizedException):
    def __init__(self):
        super().__init__("Can't decode token.")


class TokenPayload(UnauthorizedException):
    def __init__(self):
        super().__init__('Token payload is invalid.')


class TokenPayloadUser(UnauthorizedException):
    def __init__(self):
        super().__init__('Token payload does not consist user.')


class TokenExpired(UnauthorizedException):
    def __init__(self):
        super().__init__('Token expired.')
