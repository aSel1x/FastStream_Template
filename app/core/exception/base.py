class CustomException(Exception):
    def __init__(self, message: str, internal_code: int = 0, http_code: int = 500):
        super().__init__(message)
        self.internal_code = internal_code
        self.http_code = http_code
        self.message = message


class RequestInvalid(CustomException):
    def __init__(self, message: str = 'Request Invalid'):
        super().__init__(message, internal_code=0, http_code=400)


class UnauthorizedException(CustomException):
    def __init__(self, message: str = 'Unauthorized'):
        super().__init__(message, internal_code=0, http_code=401)


class NotFoundException(CustomException):
    def __init__(self, message: str = 'Not Found'):
        super().__init__(message, internal_code=0, http_code=404)


class ConflictException(CustomException):
    def __init__(self, message: str = 'Conflict'):
        super().__init__(message, internal_code=0, http_code=409)
