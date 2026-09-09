import uuid
from typing import final, override

from litestar.middleware.base import MiddlewareProtocol
from litestar.types import ASGIApp, Message, Receive, Scope, Send
from opentelemetry import trace

from infrastructure.observability.request_context import get_request_id, set_request_id

__all__ = ('RequestIDMiddleware', 'get_request_id')


@final
class RequestIDMiddleware(MiddlewareProtocol):
    """Propagates `X-Request-ID`, minting one when the caller did not send it.

    The id lands in a ContextVar, on the current span, and on the response, so a log line,
    a trace and a client-side report can all be tied to the same request.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers_list = scope['headers']
        headers_dict = dict(headers_list)
        request_id = headers_dict.get(b'x-request-id', str(uuid.uuid4()).encode()).decode()

        scope['headers'] = [*headers_list, (b'x-request-id', request_id.encode())]

        set_request_id(request_id)
        trace.get_current_span().set_attribute('request_id', request_id)

        async def send_wrapper(message: Message) -> None:
            if message['type'] == 'http.response.start':
                message['headers'] = [*message['headers'], (b'x-request-id', request_id.encode())]
            await send(message)

        await self.app(scope, receive, send_wrapper)
