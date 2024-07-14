from fastapi import Request
from fastapi.responses import JSONResponse


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str | None):
        self.status_code = status_code
        self.detail = detail


# User
USER_EXISTS = HTTPException(409, 'User is already taken.')
USER_NOT_FOUND = HTTPException(404, 'User not found.')
USER_IS_CORRECT = HTTPException(401, 'Authorization failed. Please try again')

# Token
TOKEN_INVALID = HTTPException(401, 'Invalid token')
TOKEN_EXPIRED = HTTPException(401, 'Token expired')


def exception_handler(_r: Request, exception: HTTPException):
    return JSONResponse(
        status_code=exception.status_code,
        content=dict(detail=exception.detail)
    )
