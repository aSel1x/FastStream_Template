import asyncio
from collections.abc import Awaitable, Callable
from typing import final

import httpx
from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get
from litestar.response import Response
from litestar.status_codes import HTTP_200_OK, HTTP_503_SERVICE_UNAVAILABLE
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from application.common.interfaces.system.cache import CacheInterface
from infrastructure.hydra import HydraConfig
from infrastructure.observability.metrics import CONTENT_TYPE as METRICS_CONTENT_TYPE
from infrastructure.observability.metrics import render
from presentation.http.middleware.request_id import get_request_id

CHECK_TIMEOUT_SECONDS = 3.0
CHECK_TIMEOUT_SECONDS_INT = 3

type Probe = Callable[[], Awaitable[None]]


class DependencyStatus(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class LivenessSchema(BaseModel):
    status: str
    request_id: str


class ReadinessSchema(BaseModel):
    status: str
    request_id: str
    dependencies: list[DependencyStatus]


async def _check(name: str, probe: Probe) -> DependencyStatus:
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            await probe()
    except Exception as exc:
        return DependencyStatus(name=name, ok=False, detail=type(exc).__name__)
    return DependencyStatus(name=name, ok=True)


@final
class HealthController(Controller):
    path = '/health'
    tags = ['health']

    @get('/', summary='Liveness')
    async def health(self) -> LivenessSchema:
        """Alias of /health/live, kept so existing probes keep working."""
        return LivenessSchema(status='alive', request_id=get_request_id() or 'unknown')

    @get(
        '/metrics',
        summary='Prometheus metrics',
        media_type='text/plain',
        include_in_schema=False,
    )
    async def metrics(self) -> Response[bytes]:
        return Response(content=render(), media_type=METRICS_CONTENT_TYPE)

    @get('/live', summary='Liveness: is the process up?')
    async def live(self) -> LivenessSchema:
        """Deliberately checks nothing external.

        A liveness probe that fails when the database blips gets the pod killed instead of
        letting it wait for the database to come back.
        """
        return LivenessSchema(status='alive', request_id=get_request_id() or 'unknown')

    @get('/ready', summary='Readiness: can the service actually serve traffic?')
    @inject
    async def ready(
        self,
        engine: FromDishka[AsyncEngine],
        cache: FromDishka[CacheInterface],
        http_client: FromDishka[httpx.AsyncClient],
        hydra_config: FromDishka[HydraConfig],
    ) -> Response[ReadinessSchema]:
        """Checks every dependency a request needs.

        The old endpoint reported a hardcoded "healthy" and stayed green with Postgres, Redis,
        RabbitMQ and Hydra all down — which under Kubernetes means traffic routed into a pod
        that cannot serve it.
        """

        async def check_database() -> None:
            async with engine.connect() as connection:
                _ = await connection.execute(text('SELECT 1'))

        async def check_cache() -> None:
            # Exercised through the port, not the redis client: this is the operation the
            # app actually performs, and it works for the in-memory backend too.
            probe_key = 'health:ready'
            await cache.set(probe_key, 'ok', ttl_seconds=CHECK_TIMEOUT_SECONDS_INT)
            if await cache.get(probe_key) != 'ok':
                message = 'cache did not return what it was given'
                raise RuntimeError(message)

        async def check_hydra() -> None:
            response = await http_client.get(f'{hydra_config.admin_url}/health/ready')
            _ = response.raise_for_status()

        dependencies = await asyncio.gather(
            _check('postgres', check_database),
            _check('cache', check_cache),
            _check('hydra', check_hydra),
        )
        ready = all(dependency.ok for dependency in dependencies)
        return Response(
            content=ReadinessSchema(
                status='ready' if ready else 'not ready',
                request_id=get_request_id() or 'unknown',
                dependencies=list(dependencies),
            ),
            status_code=HTTP_200_OK if ready else HTTP_503_SERVICE_UNAVAILABLE,
        )
