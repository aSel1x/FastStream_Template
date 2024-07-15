from app.core.exception.status import HTTPStatus
from app.core.exception.exception import AppException


# User
USER_EXISTS = AppException(HTTPStatus.CONFLICT, 'User is already taken.')
USER_NOT_FOUND = AppException(HTTPStatus.NOT_FOUND, 'User not found.')
USER_IS_CORRECT = AppException(HTTPStatus.UNAUTHORIZED, 'Authorization failed. Please try again')

# Token
TOKEN_INVALID = AppException(HTTPStatus.UNAUTHORIZED, 'Invalid token')
TOKEN_EXPIRED = AppException(HTTPStatus.UNAUTHORIZED, 'Token expired')
