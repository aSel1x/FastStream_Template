from sqlmodel.ext.asyncio.session import AsyncSession

from .user import UserService
from .security import Security

from app.core.config import Config


class Services:
    def __init__(self, session: AsyncSession, config: Config):
        self.user = UserService(session)
        self.security = Security(config)


__all__ = ['Services']
