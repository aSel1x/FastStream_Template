"""Unit tests for A/B-phase infrastructure fixes.

Covers:
- A3: InMemoryUoW.add_events accumulation and commit/rollback clearing.
- A5: HTTPSRedirectMiddleware redirect / passthrough / disabled behaviour.

Note: B6 (EventPublisherAMQP) and A1 (OutboxRepository) live in
``tests/e2e/test_outbox_infra.py`` alongside the rest of the infra/e2e suite.
"""

import pytest
from litestar import Litestar, get
from litestar.middleware import DefineMiddleware
from litestar.testing import TestClient

from domain.user.events import UserCreatedEvent
from infrastructure.db.memory.uow import InMemoryUoW
from presentation.http.middleware.https_redirect import HTTPSRedirectMiddleware


class TestInMemoryUoW:
    @pytest.mark.asyncio
    async def test_add_events_accumulates(self) -> None:
        uow = InMemoryUoW()
        event = UserCreatedEvent(user_id='u1', username='bob', email='b@example.com')

        uow.add_events([event])

        assert uow._pending_events == [event]

    @pytest.mark.asyncio
    async def test_commit_clears_pending_events(self) -> None:
        uow = InMemoryUoW()
        uow.add_events([UserCreatedEvent(user_id='u1', username='bob', email='b@example.com')])

        await uow.commit()

        assert uow._pending_events == []

    @pytest.mark.asyncio
    async def test_rollback_clears_pending_events(self) -> None:
        uow = InMemoryUoW()
        uow.add_events([UserCreatedEvent(user_id='u1', username='bob', email='b@example.com')])

        await uow.rollback()

        assert uow._pending_events == []

    @pytest.mark.asyncio
    async def test_add_events_appends_multiple_batches(self) -> None:
        uow = InMemoryUoW()
        first = [UserCreatedEvent(user_id='u1', username='bob', email='b@example.com')]
        second = [UserCreatedEvent(user_id='u2', username='alice', email='a@example.com')]

        uow.add_events(first)
        uow.add_events(second)

        assert len(uow._pending_events) == 2


class TestHTTPSRedirectMiddleware:
    def _make_app(self, enabled: bool) -> Litestar:
        @get('/health')
        async def health() -> dict[str, str]:
            return {'status': 'healthy'}

        return Litestar(
            route_handlers=[health],
            middleware=[DefineMiddleware(HTTPSRedirectMiddleware, enabled=enabled)],
        )

    def test_redirects_http_to_https(self) -> None:
        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get(
                '/health',
                headers={'x-forwarded-proto': 'http'},
                follow_redirects=False,
            )

            assert response.status_code == 301
            assert response.headers['location'].startswith('https://')
            assert '/health' in response.headers['location']

    def test_preserves_query_string(self) -> None:
        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get(
                '/health?code=abc123',
                headers={'x-forwarded-proto': 'http'},
                follow_redirects=False,
            )

            assert response.status_code == 301
            assert 'code=abc123' in response.headers['location']

    def test_passes_through_https(self) -> None:
        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get('/health', headers={'x-forwarded-proto': 'https'})

            assert response.status_code == 200

    def test_disabled_middleware_does_not_redirect(self) -> None:
        with TestClient(self._make_app(enabled=False)) as client:
            response = client.get('/health', headers={'x-forwarded-proto': 'http'})

            assert response.status_code == 200
