from typing import Protocol


class JWTInterface(Protocol):
    async def generate(self, payload: dict, exp: int) -> str:
        pass

    async def extract(self, token: str) -> dict:
        pass
