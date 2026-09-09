from dataclasses import dataclass
from typing import final

from application.common.interfaces import HydraAdminClientInterface


@dataclass
class ClientDTO:
    client_id: str
    client_name: str
    client_uri: str | None
    redirect_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    is_confidential: bool


@final
class ListOAuthClientsUseCase:
    def __init__(self, hydra_client: HydraAdminClientInterface) -> None:
        self._hydra_client = hydra_client

    async def __call__(self) -> list[ClientDTO]:
        clients = await self._hydra_client.list_clients()
        return [
            ClientDTO(
                client_id=c.client_id,
                client_name=c.client_name,
                client_uri=c.client_uri,
                redirect_uris=c.redirect_uris,
                grant_types=c.grant_types,
                scopes=c.scope,
                is_confidential=c.token_endpoint_auth_method != 'none',  # noqa: S105 - an OAuth2 auth-method name, not a secret
            )
            for c in clients
        ]
