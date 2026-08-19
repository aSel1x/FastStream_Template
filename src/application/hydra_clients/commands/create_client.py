from typing import final
from dataclasses import dataclass

from application.common.interfaces import HydraAdminClientInterface, HydraClientCreate


@dataclass
class CreateOAuthClientInput:
    client_name: str
    redirect_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    is_confidential: bool
    client_uri: str | None = None


@dataclass
class CreateOAuthClientOutput:
    client_id: str
    client_secret: str | None
    client_name: str
    redirect_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    is_confidential: bool


@final
class CreateOAuthClientUseCase:
    def __init__(self, hydra_client: HydraAdminClientInterface) -> None:
        self._hydra_client = hydra_client

    async def __call__(self, input: CreateOAuthClientInput) -> CreateOAuthClientOutput:
        client = await self._hydra_client.create_client(HydraClientCreate(
            client_name=input.client_name,
            client_uri=input.client_uri,
            redirect_uris=input.redirect_uris,
            grant_types=input.grant_types,
            response_types=['code'] if 'authorization_code' in input.grant_types else [],
            scope=input.scopes,
            token_endpoint_auth_method='client_secret_basic' if input.is_confidential else 'none',
        ))

        return CreateOAuthClientOutput(
            client_id=client.client_id,
            client_secret=client.client_secret,
            client_name=client.client_name,
            redirect_uris=client.redirect_uris,
            grant_types=client.grant_types,
            scopes=client.scope,
            is_confidential=client.token_endpoint_auth_method != 'none',
        )
