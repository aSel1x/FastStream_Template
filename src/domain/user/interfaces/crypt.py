from typing import Protocol


class CryptInterface(Protocol):
    async def hash(self, pwd: str) -> bytes:
        raise NotImplementedError

    async def compare_hashes(self, plain_pwd: str, hashed_pwd: bytes) -> bool:
        raise NotImplementedError
