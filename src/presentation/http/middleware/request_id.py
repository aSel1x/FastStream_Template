import uuid
from typing import final, override
from contextvars import ContextVar

from opentelemetry import trace
from litestar.middleware.base import MiddlewareProtocol
from litestar.types import ASGIApp, Message, Receive, Send, Scope

request_id_var: ContextVar[str] = ContextVar('request_id', default='')


def get_request_id() -> str:
    return request_id_var.get()


@final
class RequestIDMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @override
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers_list = scope['headers']
        headers_dict = dict(headers_list)
        request_id = headers_dict.get(b'x-request-id', str(uuid.uuid4()).encode()).decode()

        new_headers: list[tuple[bytes, bytes]] = [*headers_list, (b'x-request-id', request_id.encode())]
        scope['headers'] = new_headers

        _ = request_id_var.set(request_id)
        trace.get_current_span().set_attribute('request_id', request_id)

        async def send_wrapper(message: Message) -> None:
            if message['type'] == 'http.response.start':
                message['headers'] = [*message['headers'], (b'x-request-id', request_id.encode())]
            await send(message)

        await self.app(scope, receive, send_wrapper)
