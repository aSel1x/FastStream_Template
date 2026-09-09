import asyncio
from typing import override

import bcrypt

from domain.user.interfaces import CryptInterface


class Crypt(CryptInterface):
    """bcrypt, run off the event loop.

    `asyncio.to_thread` rather than `get_event_loop().run_in_executor(None, lambda: ...)`:
    same default executor, no deprecated loop lookup, no closure.
    """

    @override
    async def hash(self, pwd: str) -> bytes:
        return await asyncio.to_thread(bcrypt.hashpw, pwd.encode('utf-8'), bcrypt.gensalt())

    @override
    async def compare_hashes(self, plain_pwd: str, hashed_pwd: bytes) -> bool:
        return await asyncio.to_thread(bcrypt.checkpw, plain_pwd.encode('utf-8'), hashed_pwd)
