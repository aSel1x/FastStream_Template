import json

import httpx
import pytest

from infrastructure.hydra.client import HydraAdminClient
from infrastructure.hydra.config import HydraConfig
from infrastructure.hydra.exceptions import (
    HydraChallengeGoneError,
    HydraChallengeNotFoundError,
    HydraClientNotFoundError,
)
from infrastructure.hydra.schemas import HydraClientCreate


def _client(handler) -> HydraAdminClient:
    transport = httpx.MockTransport(handler)
    http = httpx.AsyncClient(base_url='http://hydra-admin', transport=transport)
    return HydraAdminClient(http, HydraConfig())


class TestLoginRequest:
    @pytest.mark.asyncio
    async def test_get_login_request_parses_fields(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params['login_challenge'] == 'chal-1'
            return httpx.Response(200, json={
                'challenge': 'chal-1',
                'client': {'client_id': 'my-client', 'client_name': 'My App'},
                'requested_scope': ['openid', 'profile'],
                'requested_access_token_audience': [],
                'skip': True,
                'subject': 'user-1',
                'session_id': 'sess-1',
            })

        result = await _client(handler).get_login_request('chal-1')
        assert result.skip is True
        assert result.subject == 'user-1'
        assert result.client.client_name == 'My App'
        assert result.requested_scope == ['openid', 'profile']

    @pytest.mark.asyncio
    async def test_get_login_request_not_found_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text='not found')

        with pytest.raises(HydraChallengeNotFoundError):
            await _client(handler).get_login_request('missing')

    @pytest.mark.asyncio
    async def test_accept_login_request_sends_subject_and_returns_redirect(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params['login_challenge'] == 'chal-1'
            body = json.loads(request.content)
            assert body['subject'] == 'user-1'
            assert body['remember'] is True
            assert body['context'] == {'user_id': 'user-1'}
            return httpx.Response(200, json={'redirect_to': 'http://hydra/oauth2/auth?x=1'})

        result = await _client(handler).accept_login_request(
            'chal-1', subject='user-1', remember=True, context={'user_id': 'user-1'},
        )
        assert result.redirect_to == 'http://hydra/oauth2/auth?x=1'

    @pytest.mark.asyncio
    async def test_accept_login_request_gone_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(410, text='gone')

        with pytest.raises(HydraChallengeGoneError):
            await _client(handler).accept_login_request('chal-1', subject='user-1')


class TestConsentRequest:
    @pytest.mark.asyncio
    async def test_accept_consent_request_sends_session_claims(self):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body['grant_scope'] == ['openid', 'email']
            assert body['session'] == {
                'id_token': {'email': 'a@example.com'},
                'access_token': {'session_id': 'sess-1'},
            }
            return httpx.Response(200, json={'redirect_to': 'http://client/callback?code=abc'})

        result = await _client(handler).accept_consent_request(
            'chal-2',
            grant_scope=['openid', 'email'],
            id_token_claims={'email': 'a@example.com'},
            access_token_claims={'session_id': 'sess-1'},
        )
        assert result.redirect_to == 'http://client/callback?code=abc'

    @pytest.mark.asyncio
    async def test_reject_consent_request(self):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body['error'] == 'access_denied'
            return httpx.Response(200, json={'redirect_to': 'http://client/callback?error=access_denied'})

        result = await _client(handler).reject_consent_request('chal-2', error='access_denied')
        assert 'error=access_denied' in result.redirect_to


class TestIntrospection:
    @pytest.mark.asyncio
    async def test_introspect_active_token(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == '/admin/oauth2/introspect'
            return httpx.Response(200, json={
                'active': True, 'sub': 'user-1', 'client_id': 'my-client',
                'scope': 'openid profile', 'aud': ['my-client'], 'exp': 123, 'iat': 100,
                'token_type': 'access_token', 'ext': {'session_id': 'sess-1'},
            })

        result = await _client(handler).introspect_token('some-token')
        assert result.active is True
        assert result.sub == 'user-1'
        assert result.ext == {'session_id': 'sess-1'}

    @pytest.mark.asyncio
    async def test_introspect_inactive_token(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={'active': False})

        result = await _client(handler).introspect_token('revoked-token')
        assert result.active is False
        assert result.sub is None


class TestClients:
    @pytest.mark.asyncio
    async def test_create_client_maps_scope_and_auth_method(self):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body['scope'] == 'openid profile'
            assert body['token_endpoint_auth_method'] == 'client_secret_basic'
            return httpx.Response(200, json={
                'client_id': 'new-client', 'client_name': 'New App', 'client_secret': 'shh',
                'redirect_uris': ['http://app/cb'], 'grant_types': ['authorization_code'],
                'response_types': ['code'], 'scope': 'openid profile',
                'token_endpoint_auth_method': 'client_secret_basic', 'created_at': '2026-01-01T00:00:00Z',
            })

        result = await _client(handler).create_client(HydraClientCreate(
            client_name='New App',
            redirect_uris=['http://app/cb'],
            grant_types=['authorization_code'],
            response_types=['code'],
            scope=['openid', 'profile'],
            token_endpoint_auth_method='client_secret_basic',
        ))
        assert result.client_id == 'new-client'
        assert result.scope == ['openid', 'profile']
        assert result.client_secret == 'shh'

    @pytest.mark.asyncio
    async def test_get_client_returns_none_on_404(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text='not found')

        result = await _client(handler).get_client('missing')
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_client_not_found_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text='not found')

        with pytest.raises(HydraClientNotFoundError):
            await _client(handler).delete_client('missing')

    @pytest.mark.asyncio
    async def test_list_clients_parses_multiple(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[
                {
                    'client_id': 'c1', 'client_name': 'App 1', 'redirect_uris': [], 'grant_types': [],
                    'response_types': [], 'scope': 'openid', 'token_endpoint_auth_method': 'none',
                },
                {
                    'client_id': 'c2', 'client_name': 'App 2', 'redirect_uris': [], 'grant_types': [],
                    'response_types': [], 'scope': '', 'token_endpoint_auth_method': 'client_secret_basic',
                },
            ])

        result = await _client(handler).list_clients()
        assert [c.client_id for c in result] == ['c1', 'c2']
        assert result[1].scope == []


class TestRevokeSessions:
    @pytest.mark.asyncio
    async def test_revoke_login_sessions_sends_subject(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == 'DELETE'
            assert request.url.path == '/admin/oauth2/auth/sessions/login'
            assert request.url.params['subject'] == 'user-1'
            return httpx.Response(204)

        await _client(handler).revoke_login_sessions('user-1')

    @pytest.mark.asyncio
    async def test_revoke_consent_sessions_sends_subject(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == 'DELETE'
            assert request.url.path == '/admin/oauth2/auth/sessions/consent'
            assert request.url.params['subject'] == 'user-1'
            return httpx.Response(204)

        await _client(handler).revoke_consent_sessions('user-1')

    @pytest.mark.asyncio
    async def test_revoke_sessions_treats_404_as_noop(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text='no active session')

        await _client(handler).revoke_login_sessions('user-1')
        await _client(handler).revoke_consent_sessions('user-1')
