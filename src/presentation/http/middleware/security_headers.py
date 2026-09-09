from typing import final, override

from litestar.datastructures import MutableScopeHeaders
from litestar.middleware.base import MiddlewareProtocol
from litestar.types import ASGIApp, Message, Receive, Scope, Send

# The Hydra consent screen is the one page in this service that a user is asked to trust.
# Without frame-ancestors it can be framed and clickjacked into granting scopes.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'"
)

BASE_HEADERS: dict[str, str] = {
    'x-frame-options': 'DENY',
    'x-content-type-options': 'nosniff',
    'referrer-policy': 'no-referrer',
    'cross-origin-opener-policy': 'same-origin',
    'permissions-policy': 'geolocation=(), microphone=(), camera=()',
    'content-security-policy': CONTENT_SECURITY_POLICY,
}

HSTS_HEADER = 'max-age=63072000; includeSubDomains'


@final
class SecurityHeadersMiddleware(MiddlewareProtocol):
    """Adds the response headers every browser-facing auth service is expected to send."""

    def __init__(self, app: ASGIApp, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_with_headers(message: Message) -> None:
            if message['type'] == 'http.response.start':
                headers = MutableScopeHeaders(message)
                to_set = dict(BASE_HEADERS)
                # Only meaningful over TLS, and actively harmful to set in local http dev.
                if self.hsts:
                    to_set['strict-transport-security'] = HSTS_HEADER
                for name, value in to_set.items():
                    if name not in headers:
                        headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)
