"""HTTP e2e tests."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from litestar import Litestar, Request, get
from litestar.testing import TestClient


@pytest.fixture
def app():
    @get('/health')
    async def health(request: Request[Any, Any, Any]) -> dict:
        return {
            'status': 'healthy',
            'version': '1.0.0',
            'request_id': 'test-request-id',
        }

    return Litestar(route_handlers=[health], debug=True)


@pytest.fixture
def client(app):
    return TestClient(app, raise_server_exceptions=False)


class TestHealth:
    def test_health_returns_200(self, client: TestClient) -> None:
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['version'] == '1.0.0'

    def test_health_includes_request_id(self, client: TestClient) -> None:
        response = client.get('/health')
        data = response.json()
        assert 'request_id' in data


class TestFullApp:
    """Tests that boot the real Litestar app (routes, DI graph, middleware) without live infra."""

    def test_full_app_health(self) -> None:
        with (
            patch('presentation.http.app.seed_oauth_clients', AsyncMock()),
            patch('presentation.http.app.seed_admin_role', AsyncMock()),
        ):
            from presentation.http.app import get_litestar

            app = get_litestar()
            client = TestClient(app, raise_server_exceptions=False)
            response = client.get('/health')
            assert response.status_code == 200


class TestParameterAliases:
    """Pins the wire names of parameters whose alias differs from the Python name.

    Litestar 2.22 deprecated the inferred parameter styles and suggests `FromHeader[T]` as
    the replacement. `FromHeader` derives the header name from the *parameter* name, so
    `idempotency_key: FromHeader[str | None]` silently reads a header called
    `idempotency_key` and returns `None` for every real `Idempotency-Key` request — no
    error, no warning, just idempotency quietly switched off. The alias has to stay
    explicit, and this test is what says so.
    """

    @staticmethod
    def _header_parameters() -> set[tuple[str, str, str]]:
        with (
            patch('presentation.http.app.seed_oauth_clients', AsyncMock()),
            patch('presentation.http.app.seed_admin_role', AsyncMock()),
        ):
            from presentation.http.app import get_litestar

            schema = get_litestar().openapi_schema.to_schema()

        return {
            (method.upper(), path, parameter['name'])
            for path, operations in schema['paths'].items()
            for method, operation in operations.items()
            if isinstance(operation, dict)
            for parameter in operation.get('parameters') or []
            if parameter.get('in') == 'header'
        }

    def test_register_reads_the_idempotency_key_header(self) -> None:
        assert ('POST', '/v1/users/register', 'Idempotency-Key') in self._header_parameters()
