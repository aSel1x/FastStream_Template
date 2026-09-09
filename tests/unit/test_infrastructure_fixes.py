"""Unit tests for A/B-phase infrastructure fixes.

Covers:
- A3: InMemoryUoW.add_events accumulation and commit/rollback clearing.
- A5: HTTPSRedirectMiddleware redirect / passthrough / disabled behaviour.

Note: B6 (EventPublisherAMQP) and A1 (OutboxRepository) live in
``tests/e2e/test_outbox_infra.py`` alongside the rest of the infra/e2e suite.
"""

from uuid import NAMESPACE_URL, UUID, uuid5

import pytest
from litestar import Litestar, get
from litestar.middleware import DefineMiddleware
from litestar.testing import TestClient

from domain.user.events import UserCreatedEvent
from infrastructure.db.memory.uow import InMemoryUoW
from presentation.http.middleware.https_redirect import HTTPSRedirectMiddleware


def _created_event(seed: str = 'u1') -> UserCreatedEvent:
    return UserCreatedEvent(user_id=_uid(seed), username='bob', email='b@example.com')


def _uid(seed: str) -> UUID:
    """A stable UUID per seed, so assertions can compare ids without hardcoding one."""
    return uuid5(NAMESPACE_URL, seed)


class TestInMemoryUoW:
    @pytest.mark.asyncio
    async def test_add_events_accumulates(self) -> None:
        uow = InMemoryUoW()
        event = UserCreatedEvent(user_id=_uid('u1'), username='bob', email='b@example.com')

        uow.add_events([event])

        assert uow._pending_events == [event]

    @pytest.mark.asyncio
    async def test_commit_clears_pending_events(self) -> None:
        uow = InMemoryUoW()
        uow.add_events([_created_event()])

        await uow.commit()

        assert uow._pending_events == []

    @pytest.mark.asyncio
    async def test_rollback_clears_pending_events(self) -> None:
        uow = InMemoryUoW()
        uow.add_events([_created_event()])

        await uow.rollback()

        assert uow._pending_events == []

    @pytest.mark.asyncio
    async def test_add_events_appends_multiple_batches(self) -> None:
        uow = InMemoryUoW()
        first = [UserCreatedEvent(user_id=_uid('u1'), username='bob', email='b@example.com')]
        second = [UserCreatedEvent(user_id=_uid('u2'), username='alice', email='a@example.com')]

        uow.add_events(first)
        uow.add_events(second)

        assert len(uow._pending_events) == 2


class TestHTTPSRedirectMiddleware:
    @pytest.fixture(autouse=True)
    def _pin_public_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # `Host` is attacker-controlled, so the middleware only redirects to a host it was
        # told about up front.
        monkeypatch.setenv('PUBLIC_HOST', 'app.example.com')

    def _make_app(self, enabled: bool) -> Litestar:
        @get('/private')
        async def private() -> dict[str, str]:
            return {'status': 'ok'}

        @get('/health/live')
        async def live() -> dict[str, str]:
            return {'status': 'alive'}

        return Litestar(
            route_handlers=[private, live],
            middleware=[DefineMiddleware(HTTPSRedirectMiddleware, enabled=enabled)],
        )

    def test_redirects_http_to_https(self) -> None:
        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get(
                '/private',
                headers={'x-forwarded-proto': 'http'},
                follow_redirects=False,
            )

            assert response.status_code == 301
            assert response.headers['location'].startswith('https://app.example.com')
            assert '/private' in response.headers['location']

    def test_refuses_to_redirect_to_an_unknown_host(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv('PUBLIC_HOST', raising=False)
        monkeypatch.setenv('ALLOWED_HOSTS', 'app.example.com')

        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get(
                '/private',
                headers={'x-forwarded-proto': 'http', 'host': 'evil.example.net'},
                follow_redirects=False,
            )

            assert response.status_code == 400, 'reflecting Host would be an open redirect'

    def test_allows_an_allowed_host_that_carries_a_port(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`Host` routinely arrives as `example.com:443`, which must still match the list."""
        monkeypatch.delenv('PUBLIC_HOST', raising=False)
        monkeypatch.setenv('ALLOWED_HOSTS', 'app.example.com')

        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get(
                '/private',
                headers={'x-forwarded-proto': 'http', 'host': 'app.example.com:443'},
                follow_redirects=False,
            )

            assert response.status_code == 301
            # The port belongs to the HTTP request, not to the https:// target.
            assert response.headers['location'] == 'https://app.example.com/private'

    def test_probe_paths_are_never_redirected(self) -> None:
        """A probe reaches the container directly, without `X-Forwarded-Proto`.

        Redirecting it makes a healthy container report itself dead -- the Docker HEALTHCHECK
        follows the 301 to a host it cannot resolve, or gets a flat 400 when no `PUBLIC_HOST`
        is configured.
        """
        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get('/health/live', follow_redirects=False)

            assert response.status_code == 200
            assert response.json() == {'status': 'alive'}

    def test_preserves_query_string(self) -> None:
        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get(
                '/private?code=abc123',
                headers={'x-forwarded-proto': 'http'},
                follow_redirects=False,
            )

            assert response.status_code == 301
            assert 'code=abc123' in response.headers['location']

    def test_passes_through_https(self) -> None:
        with TestClient(self._make_app(enabled=True)) as client:
            response = client.get('/private', headers={'x-forwarded-proto': 'https'})

            assert response.status_code == 200

    def test_disabled_middleware_does_not_redirect(self) -> None:
        with TestClient(self._make_app(enabled=False)) as client:
            response = client.get('/private', headers={'x-forwarded-proto': 'http'})

            assert response.status_code == 200
