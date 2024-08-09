from .base import ConflictException, NotFoundException, UnauthorizedException


class NotFound(NotFoundException):
    def __init__(self):
        super().__init__('User not found')


class UsernameTaken(ConflictException):
    def __init__(self):
        super().__init__('Username taken')


class PasswordWrong(UnauthorizedException):
    def __init__(self):
        super().__init__('Password wrong')
