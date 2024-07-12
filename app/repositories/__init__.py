from sqlmodel.ext.asyncio.session import AsyncSession

from .user import UserRepository


class Repositories:
    def __init__(self, session: AsyncSession):
        self.user = UserRepository(session)


__all__ = ['Repositories', ]
