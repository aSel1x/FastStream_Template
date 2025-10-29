import asyncio
from typing import override

import bcrypt
from domain.user.interfaces import CryptInterface


class Crypt(CryptInterface):
    @override
    async def hash(self, pwd: str) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: bcrypt.hashpw(pwd.encode('utf-8'), bcrypt.gensalt())
        )

    @override
    async def compare_hashes(self, plain_pwd: str, hashed_pwd: bytes) -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: bcrypt.checkpw(plain_pwd.encode('utf-8'), hashed_pwd)
        )
