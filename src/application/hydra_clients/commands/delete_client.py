from typing import final
from application.common.exceptions import OAuthClientNotFoundError
from application.common.interfaces import HydraAdminClientInterface
from infrastructure.hydra import HydraClientNotFoundError


@final
class DeleteOAuthClientUseCase:
    def __init__(self, hydra_client: HydraAdminClientInterface) -> None:
        self._hydra_client = hydra_client

    async def __call__(self, client_id: str) -> None:
        try:
            await self._hydra_client.delete_client(client_id)
        except HydraClientNotFoundError as e:
            raise OAuthClientNotFoundError(client_id) from e
