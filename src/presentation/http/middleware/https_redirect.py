from typing import final, override
from litestar.middleware.base import MiddlewareProtocol
from litestar.response.redirect import ASGIRedirectResponse
from litestar.status_codes import HTTP_301_MOVED_PERMANENTLY
from litestar.types import ASGIApp, Receive, Send, Scope


@final
class HTTPSRedirectMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp, enabled: bool = True) -> None:
        self.app = app
        self.enabled = enabled

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.enabled:
            await self.app(scope, receive, send)
            return

        headers = {k.decode('latin-1').lower(): v.decode('latin-1') for k, v in scope['headers']}
        x_forwarded_proto = headers.get('x-forwarded-proto', 'http')

        if x_forwarded_proto != 'https':
            host = headers.get('host', 'localhost')
            path = scope['path']
            query = scope['query_string'].decode()

            redirect_url = f"https://{host}{path}"
            if query:
                redirect_url += f"?{query}"

            response = ASGIRedirectResponse(
                path=redirect_url,
                status_code=HTTP_301_MOVED_PERMANENTLY,
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)