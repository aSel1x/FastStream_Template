import os
from typing import final, override

from litestar.middleware.base import MiddlewareProtocol
from litestar.response.base import ASGIResponse
from litestar.response.redirect import ASGIRedirectResponse
from litestar.status_codes import HTTP_301_MOVED_PERMANENTLY, HTTP_400_BAD_REQUEST
from litestar.types import ASGIApp, Receive, Scope, Send


@final
class HTTPSRedirectMiddleware(MiddlewareProtocol):
    """Redirects plain HTTP to HTTPS.

    `Host` is attacker-controlled, so reflecting it into the `Location` header turns this into
    an open redirect. `PUBLIC_HOST` pins the host to redirect to; without it the middleware
    keeps the request's host only when it is in `ALLOWED_HOSTS`, and otherwise refuses.
    """

    def __init__(self, app: ASGIApp, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled
        self.public_host: str | None = os.getenv('PUBLIC_HOST') or None
        self.allowed_hosts: frozenset[str] = frozenset(
            entry.strip().lower()
            for entry in os.getenv('ALLOWED_HOSTS', '').split(',')
            if entry.strip()
        )

    def _redirect_host(self, request_host: str) -> str | None:
        if self.public_host:
            return self.public_host
        if request_host.lower() in self.allowed_hosts:
            return request_host
        return None

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enabled:
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

            path = scope['path']
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
