from typing import final

import httpx
from pydantic import JsonValue, TypeAdapter

from application.common.interfaces.acl.hydra_admin import ProviderClientNotFoundError
from infrastructure.hydra.config import HydraConfig
from infrastructure.hydra.exceptions import (
    HydraAdminError,
    HydraChallengeGoneError,
    HydraChallengeNotFoundError,
    HydraClientNotFoundError,
)
from infrastructure.hydra.schemas import (
    HydraClient,
    HydraClientCreate,
    HydraConsentRequest,
    HydraIntrospection,
    HydraLoginRequest,
    HydraLogoutRequest,
    HydraRedirect,
)

_hydra_client_list_adapter = TypeAdapter(list[HydraClient])


def _raise_for_status(
    response: httpx.Response, *, not_found_error: type[HydraAdminError] = HydraAdminError
) -> None:
    if response.status_code < 400:
        return
    if response.status_code == 404:
        raise not_found_error(response.status_code, response.text)
    if response.status_code == 410:
        raise HydraChallengeGoneError(response.status_code, response.text)
    raise HydraAdminError(response.status_code, response.text)


def _raise_client_status(response: httpx.Response) -> None:
    """Like `_raise_for_status`, but presents Hydra's 404 as the port's own error.

    The anti-corruption boundary: a use case catches `ProviderClientNotFoundError` and stays
    ignorant of which authorization server is behind the port.
    """
    try:
        _raise_for_status(response, not_found_error=HydraClientNotFoundError)
    except HydraClientNotFoundError as exc:
        raise ProviderClientNotFoundError(str(exc)) from exc


def _client_to_wire(data: HydraClientCreate) -> dict[str, JsonValue]:
    payload: dict[str, JsonValue] = {
        'client_name': data.client_name,
        'redirect_uris': [*data.redirect_uris],
        'grant_types': [*data.grant_types],
        'response_types': [*data.response_types],
        'scope': ' '.join(data.scope),
        'token_endpoint_auth_method': data.token_endpoint_auth_method,
    }
    if data.client_uri:
        payload['client_uri'] = data.client_uri
    if data.client_id:
        payload['client_id'] = data.client_id
    if data.client_secret:
        payload['client_secret'] = data.client_secret
    return payload


@final
class HydraAdminClient:
    def __init__(self, http: httpx.AsyncClient, config: HydraConfig) -> None:
        self._http = http
        self._config = config

    async def get_login_request(self, login_challenge: str) -> HydraLoginRequest:
        response = await self._http.get(
            '/admin/oauth2/auth/requests/login',
            params={'login_challenge': login_challenge},
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)
        return HydraLoginRequest.model_validate_json(response.text)

    async def accept_login_request(
        self,
        login_challenge: str,
        *,
        subject: str,
        remember: bool = False,
        remember_for: int = 0,
        acr: str | None = None,
        amr: list[str] | None = None,
        context: dict[str, JsonValue] | None = None,
    ) -> HydraRedirect:
        body: dict[str, JsonValue] = {
            'subject': subject,
            'remember': remember,
            'remember_for': remember_for,
        }
        if acr:
            body['acr'] = acr
        if amr:
            body['amr'] = [*amr]
        if context is not None:
            body['context'] = context
        response = await self._http.put(
            '/admin/oauth2/auth/requests/login/accept',
            params={'login_challenge': login_challenge},
            json=body,
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)
        return HydraRedirect.model_validate_json(response.text)

    async def reject_login_request(
        self,
        login_challenge: str,
        *,
        error: str = 'access_denied',
        error_description: str = '',
    ) -> HydraRedirect:
        response = await self._http.put(
            '/admin/oauth2/auth/requests/login/reject',
            params={'login_challenge': login_challenge},
            json={'error': error, 'error_description': error_description},
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)
        return HydraRedirect.model_validate_json(response.text)

    async def get_consent_request(self, consent_challenge: str) -> HydraConsentRequest:
        response = await self._http.get(
            '/admin/oauth2/auth/requests/consent',
            params={'consent_challenge': consent_challenge},
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)
        return HydraConsentRequest.model_validate_json(response.text)

    async def accept_consent_request(
        self,
        consent_challenge: str,
        *,
        grant_scope: list[str],
        grant_access_token_audience: list[str] | None = None,
        remember: bool = False,
        remember_for: int = 0,
        id_token_claims: dict[str, JsonValue] | None = None,
        access_token_claims: dict[str, JsonValue] | None = None,
    ) -> HydraRedirect:
        body: dict[str, JsonValue] = {
            'grant_scope': [*grant_scope],
            'remember': remember,
            'remember_for': remember_for,
        }
        if grant_access_token_audience is not None:
            body['grant_access_token_audience'] = [*grant_access_token_audience]
        if id_token_claims or access_token_claims:
            body['session'] = {
                'id_token': id_token_claims or {},
                'access_token': access_token_claims or {},
            }
        response = await self._http.put(
            '/admin/oauth2/auth/requests/consent/accept',
            params={'consent_challenge': consent_challenge},
            json=body,
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)
        return HydraRedirect.model_validate_json(response.text)

    async def reject_consent_request(
        self,
        consent_challenge: str,
        *,
        error: str = 'access_denied',
        error_description: str = '',
    ) -> HydraRedirect:
        response = await self._http.put(
            '/admin/oauth2/auth/requests/consent/reject',
            params={'consent_challenge': consent_challenge},
            json={'error': error, 'error_description': error_description},
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)
        return HydraRedirect.model_validate_json(response.text)

    async def get_logout_request(self, logout_challenge: str) -> HydraLogoutRequest:
        response = await self._http.get(
            '/admin/oauth2/auth/requests/logout',
            params={'logout_challenge': logout_challenge},
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)
        return HydraLogoutRequest.model_validate_json(response.text)

    async def accept_logout_request(self, logout_challenge: str) -> HydraRedirect:
        response = await self._http.put(
            '/admin/oauth2/auth/requests/logout/accept',
            params={'logout_challenge': logout_challenge},
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)
        return HydraRedirect.model_validate_json(response.text)

    async def reject_logout_request(self, logout_challenge: str) -> None:
        response = await self._http.put(
            '/admin/oauth2/auth/requests/logout/reject',
            params={'logout_challenge': logout_challenge},
        )
        _raise_for_status(response, not_found_error=HydraChallengeNotFoundError)

    async def revoke_login_sessions(self, subject: str) -> None:
        response = await self._http.delete(
            '/admin/oauth2/auth/sessions/login',
            params={'subject': subject},
        )
        if response.status_code == 404:
            return
        _raise_for_status(response)

    async def revoke_consent_sessions(self, subject: str) -> None:
        response = await self._http.delete(
            '/admin/oauth2/auth/sessions/consent',
            params={'subject': subject},
        )
        if response.status_code == 404:
            return
        _raise_for_status(response)

    async def introspect_token(self, token: str, scope: str | None = None) -> HydraIntrospection:
        data = {'token': token, 'token_type_hint': 'access_token'}
        if scope:
            data['scope'] = scope
        response = await self._http.post('/admin/oauth2/introspect', data=data)
        _raise_for_status(response)
        return HydraIntrospection.model_validate_json(response.text)

    async def create_client(self, data: HydraClientCreate) -> HydraClient:
        response = await self._http.post('/admin/clients', json=_client_to_wire(data))
        _raise_for_status(response)
        return HydraClient.model_validate_json(response.text)

    async def get_client(self, client_id: str) -> HydraClient | None:
        response = await self._http.get(f'/admin/clients/{client_id}')
        if response.status_code == 404:
            return None
        _raise_for_status(response, not_found_error=HydraClientNotFoundError)
        return HydraClient.model_validate_json(response.text)

    async def list_clients(self, page_size: int = 100) -> list[HydraClient]:
        response = await self._http.get('/admin/clients', params={'page_size': page_size})
        _raise_for_status(response)
        return _hydra_client_list_adapter.validate_json(response.text)

    async def delete_client(self, client_id: str) -> None:
        response = await self._http.delete(f'/admin/clients/{client_id}')
        _raise_client_status(response)

    async def rotate_client_secret(self, client_id: str) -> HydraClient:
        response = await self._http.post(f'/admin/clients/{client_id}/secrets/rotate')
        _raise_client_status(response)
        return HydraClient.model_validate_json(response.text)
