from sqlmodel.ext.asyncio.session import AsyncSession

from .user import UserService


class Services:
    def __init__(self, session: AsyncSession):
        self.user = UserService(session)


__all__ = ['Services']
