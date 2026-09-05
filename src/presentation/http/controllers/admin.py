from typing import final

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, delete, get, post
from pydantic import BaseModel

from application.hydra_clients.commands.create_client import (
    CreateOAuthClientInput,
    CreateOAuthClientUseCase,
)
from application.hydra_clients.commands.delete_client import DeleteOAuthClientUseCase
from application.hydra_clients.commands.rotate_client_secret import RotateClientSecretUseCase
from application.hydra_clients.queries.list_clients import ListOAuthClientsUseCase
from presentation.http.guards import require_admin


class CreateClientRequest(BaseModel):
    client_name: str
    redirect_uris: list[str] = []
    grant_types: list[str] = ['authorization_code']
    scopes: list[str] = ['openid', 'profile', 'email']
    is_confidential: bool = False
    client_uri: str | None = None


class CreateClientResponse(BaseModel):
    client_id: str
    client_secret: str | None = None
    client_name: str
    redirect_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    is_confidential: bool


class ClientResponse(BaseModel):
    client_id: str
    client_name: str
    client_uri: str | None = None
    redirect_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    is_confidential: bool


class RotateSecretResponse(BaseModel):
    client_id: str
    client_secret: str | None = None


@final
class AdminClientsController(Controller):
    path = '/admin/clients'
    guards = [require_admin]

    @post('/')
    @inject
    async def create_client(
        self,
        data: CreateClientRequest,
        use_case: FromDishka[CreateOAuthClientUseCase],
    ) -> CreateClientResponse:
        result = await use_case(
            CreateOAuthClientInput(
                client_name=data.client_name,
                redirect_uris=data.redirect_uris,
                grant_types=data.grant_types,
                scopes=data.scopes,
                is_confidential=data.is_confidential,
                client_uri=data.client_uri,
            )
        )
        return CreateClientResponse(
            client_id=result.client_id,
            client_secret=result.client_secret,
            client_name=result.client_name,
            redirect_uris=result.redirect_uris,
            grant_types=result.grant_types,
            scopes=result.scopes,
            is_confidential=result.is_confidential,
        )

    @get('/')
    @inject
    async def list_clients(
        self,
        use_case: FromDishka[ListOAuthClientsUseCase],
    ) -> list[ClientResponse]:
        clients = await use_case()
        return [
            ClientResponse(
                client_id=c.client_id,
                client_name=c.client_name,
                client_uri=c.client_uri,
                redirect_uris=c.redirect_uris,
                grant_types=c.grant_types,
                scopes=c.scopes,
                is_confidential=c.is_confidential,
            )
            for c in clients
        ]

    @delete('/{client_id: str}', status_code=200)
    @inject
    async def delete_client(
        self,
        client_id: str,
        use_case: FromDishka[DeleteOAuthClientUseCase],
    ) -> dict[str, str]:
        await use_case(client_id)
        return {'message': f'Client "{client_id}" deleted'}

    @post('/{client_id: str}/rotate')
    @inject
    async def rotate_secret(
        self,
        client_id: str,
        use_case: FromDishka[RotateClientSecretUseCase],
    ) -> RotateSecretResponse:
        result = await use_case(client_id)
        return RotateSecretResponse(
            client_id=result.client_id,
            client_secret=result.client_secret,
        )
