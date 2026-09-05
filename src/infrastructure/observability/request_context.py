"""The correlation id for the work in flight.

A ContextVar rather than a parameter threaded through every call, and here rather than in
`presentation/`: logging and tracing both need it, and infrastructure may not import
presentation. The HTTP middleware sets it; anything can read it.
"""

from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar('request_id', default='')


def get_request_id() -> str:
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    _ = request_id_var.set(request_id)
