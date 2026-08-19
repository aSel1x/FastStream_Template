from typing import final
from dataclasses import dataclass

from application.common.exceptions import OAuthClientNotFoundError
from application.common.interfaces import HydraAdminClientInterface
from infrastructure.hydra import HydraClientNotFoundError


@dataclass
class RotateClientSecretOutput:
    client_id: str
    client_secret: str | None


@final
class RotateClientSecretUseCase:
    def __init__(self, hydra_client: HydraAdminClientInterface) -> None:
        self._hydra_client = hydra_client

    async def __call__(self, client_id: str) -> RotateClientSecretOutput:
        try:
            client = await self._hydra_client.rotate_client_secret(client_id)
        except HydraClientNotFoundError as e:
            raise OAuthClientNotFoundError(client_id) from e

        return RotateClientSecretOutput(
            client_id=client.client_id,
            client_secret=client.client_secret,
        )
