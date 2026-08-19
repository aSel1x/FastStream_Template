from unittest.mock import AsyncMock

import pytest

from application.common.exceptions import OAuthClientNotFoundError
from application.hydra_clients.commands.create_client import CreateOAuthClientInput, CreateOAuthClientUseCase
from application.hydra_clients.commands.delete_client import DeleteOAuthClientUseCase
from application.hydra_clients.commands.rotate_client_secret import RotateClientSecretUseCase
from application.hydra_clients.queries.list_clients import ListOAuthClientsUseCase
from infrastructure.hydra.exceptions import HydraClientNotFoundError
from infrastructure.hydra.schemas import HydraClient


def _make_client(**overrides) -> HydraClient:
    defaults = dict(
        client_id='client-1', client_name='App', client_secret='shh', client_uri=None,
        redirect_uris=['http://app/cb'], grant_types=['authorization_code'], response_types=['code'],
        scope=['openid', 'profile'], token_endpoint_auth_method='client_secret_basic', created_at=None,
    )
    defaults.update(overrides)
    return HydraClient(**defaults)


class TestCreateOAuthClientUseCase:
    @pytest.mark.asyncio
    async def test_maps_confidential_to_client_secret_basic(self):
        hydra_client = AsyncMock()
        hydra_client.create_client = AsyncMock(return_value=_make_client())

        use_case = CreateOAuthClientUseCase(hydra_client)
        result = await use_case(CreateOAuthClientInput(
            client_name='App', redirect_uris=['http://app/cb'], grant_types=['authorization_code'],
            scopes=['openid', 'profile'], is_confidential=True,
        ))

        call_arg = hydra_client.create_client.await_args.args[0]
        assert call_arg.token_endpoint_auth_method == 'client_secret_basic'
        assert call_arg.response_types == ['code']
        assert result.is_confidential is True
        assert result.client_secret == 'shh'

    @pytest.mark.asyncio
    async def test_public_client_maps_to_none_auth_method(self):
        hydra_client = AsyncMock()
        hydra_client.create_client = AsyncMock(
            return_value=_make_client(client_secret=None, token_endpoint_auth_method='none'),
        )

        use_case = CreateOAuthClientUseCase(hydra_client)
        result = await use_case(CreateOAuthClientInput(
            client_name='App', redirect_uris=[], grant_types=['authorization_code'],
            scopes=['openid'], is_confidential=False,
        ))

        call_arg = hydra_client.create_client.await_args.args[0]
        assert call_arg.token_endpoint_auth_method == 'none'
        assert result.is_confidential is False
        assert result.client_secret is None


class TestDeleteOAuthClientUseCase:
    @pytest.mark.asyncio
    async def test_deletes_client(self):
        hydra_client = AsyncMock()
        use_case = DeleteOAuthClientUseCase(hydra_client)

        await use_case('client-1')

        hydra_client.delete_client.assert_awaited_once_with('client-1')

    @pytest.mark.asyncio
    async def test_translates_not_found(self):
        hydra_client = AsyncMock()
        hydra_client.delete_client = AsyncMock(side_effect=HydraClientNotFoundError(404, 'not found'))

        use_case = DeleteOAuthClientUseCase(hydra_client)

        with pytest.raises(OAuthClientNotFoundError):
            await use_case('missing')


class TestRotateClientSecretUseCase:
    @pytest.mark.asyncio
    async def test_rotates_secret(self):
        hydra_client = AsyncMock()
        hydra_client.rotate_client_secret = AsyncMock(return_value=_make_client(client_secret='new-secret'))

        use_case = RotateClientSecretUseCase(hydra_client)
        result = await use_case('client-1')

        assert result.client_secret == 'new-secret'

    @pytest.mark.asyncio
    async def test_translates_not_found(self):
        hydra_client = AsyncMock()
        hydra_client.rotate_client_secret = AsyncMock(side_effect=HydraClientNotFoundError(404, 'not found'))

        use_case = RotateClientSecretUseCase(hydra_client)

        with pytest.raises(OAuthClientNotFoundError):
            await use_case('missing')


class TestListOAuthClientsUseCase:
    @pytest.mark.asyncio
    async def test_lists_and_maps_clients(self):
        hydra_client = AsyncMock()
        hydra_client.list_clients = AsyncMock(return_value=[_make_client(), _make_client(client_id='client-2')])

        use_case = ListOAuthClientsUseCase(hydra_client)
        result = await use_case()

        assert [c.client_id for c in result] == ['client-1', 'client-2']
        assert result[0].is_confidential is True
