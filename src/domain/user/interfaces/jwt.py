from typing import Protocol


class JWTInterface(Protocol):
    async def generate(self, payload: dict[str, str], exp: int) -> str:
        raise NotImplementedError

    async def extract(self, token: str) -> dict[str, str]:
        raise NotImplementedError
