from app.core.exception.status import HTTPStatus
from app.core.exception.http import HTTPException


# User
USER_EXISTS = HTTPException(HTTPStatus.CONFLICT, 'User is already taken.')
USER_NOT_FOUND = HTTPException(HTTPStatus.NOT_FOUND, 'User not found.')
USER_IS_CORRECT = HTTPException(HTTPStatus.UNAUTHORIZED, 'Authorization failed. Please try again')

# Token
TOKEN_INVALID = HTTPException(HTTPStatus.UNAUTHORIZED, 'Invalid token')
TOKEN_EXPIRED = HTTPException(HTTPStatus.UNAUTHORIZED, 'Token expired')
