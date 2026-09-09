import os
from typing import final, override

from litestar.middleware.base import MiddlewareProtocol
from litestar.response.base import ASGIResponse
from litestar.response.redirect import ASGIRedirectResponse
from litestar.status_codes import HTTP_301_MOVED_PERMANENTLY, HTTP_400_BAD_REQUEST
from litestar.types import ASGIApp, Receive, Scope, Send

#: Everything the health controller serves: liveness, readiness and metrics.
PROBE_PATH = '/health'


def _normalise_host(host: str) -> str:
    """The bare host from a `Host` header, which may carry a port.

    `ALLOWED_HOSTS` holds hostnames, but browsers and proxies send `example.com:443`, so a
    literal comparison rejects the very host the operator allow-listed. The port is dropped
    from the redirect target too -- it is the *HTTP* port, and carrying it into an https://
    URL would produce `https://example.com:80`.
    """
    host = host.strip().lower()
    if host.startswith('['):  # IPv6 literal, e.g. [::1]:8000
        end = host.find(']')
        if end != -1:
            return host[: end + 1]
    return host.partition(':')[0]


@final
class HTTPSRedirectMiddleware(MiddlewareProtocol):
    """Redirects plain HTTP to HTTPS.

    `Host` is attacker-controlled, so reflecting it into the `Location` header turns this into
    an open redirect. `PUBLIC_HOST` pins the host to redirect to; without it the middleware
    keeps the request's host only when it is in `ALLOWED_HOSTS`, and otherwise refuses.

    Probe paths are exempt. A liveness or readiness probe reaches the container directly over
    the internal network, in plain HTTP and without `X-Forwarded-Proto`, so redirecting it
    makes a healthy container look dead: the Docker HEALTHCHECK follows the 301 to a host it
    cannot resolve, and a deployment with no `PUBLIC_HOST` gets a flat 400 instead.
    """

    def __init__(self, app: ASGIApp, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled
        self.public_host: str | None = os.getenv('PUBLIC_HOST') or None
        self.allowed_hosts: frozenset[str] = frozenset(
            _normalise_host(entry)
            for entry in os.getenv('ALLOWED_HOSTS', '').split(',')
            if entry.strip()
        )

    def _redirect_host(self, request_host: str) -> str | None:
        if self.public_host:
            return self.public_host
        host = _normalise_host(request_host)
        if host in self.allowed_hosts:
            return host
        return None

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enabled:
            await self.app(scope, receive, send)
            return

        path: str = scope['path']
        if path == PROBE_PATH or path.startswith(f'{PROBE_PATH}/'):
            await self.app(scope, receive, send)
            return

        headers = {k.decode('latin-1').lower(): v.decode('latin-1') for k, v in scope['headers']}
        x_forwarded_proto = headers.get('x-forwarded-proto', 'http')

        if x_forwarded_proto != 'https':
            host = self._redirect_host(headers.get('host', ''))
            if host is None:
                response = ASGIResponse(
                    body=b'Unrecognised host',
                    status_code=HTTP_400_BAD_REQUEST,
                    media_type='text/plain',
                )
                await response(scope, receive, send)
                return

            query = scope['query_string'].decode()

            redirect_url = f'https://{host}{path}'
            if query:
                redirect_url += f'?{query}'

            response = ASGIRedirectResponse(
                path=redirect_url,
                status_code=HTTP_301_MOVED_PERMANENTLY,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
