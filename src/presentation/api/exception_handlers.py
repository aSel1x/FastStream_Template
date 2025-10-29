from __future__ import annotations

from typing import TYPE_CHECKING

from domain.common.exception import BaseAppError
from litestar import Response
from litestar.datastructures.state import State
from litestar.status_codes import HTTP_400_BAD_REQUEST

if TYPE_CHECKING:
    from litestar import Request


def app_exception_handler(
    _request: Request[object, object, State],
    exc: BaseAppError,
) -> Response[dict[str, str]]:
    status_code = getattr(exc, 'status', HTTP_400_BAD_REQUEST)

    return Response(
        content={
            'error': exc.__class__.__name__,
            'detail': exc.detail,
        },
        status_code=status_code,
    )


__all__ = ['app_exception_handler']
