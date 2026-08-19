"""HTTP e2e tests."""
from unittest.mock import AsyncMock, patch

import pytest
from typing import Any

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
        with patch('presentation.http.app.seed_oauth_clients', AsyncMock()):
            with patch('presentation.http.app.seed_admin_role', AsyncMock()):
                from presentation.http.app import get_litestar
                app = get_litestar()
                client = TestClient(app, raise_server_exceptions=False)
                response = client.get('/health')
                assert response.status_code == 200
