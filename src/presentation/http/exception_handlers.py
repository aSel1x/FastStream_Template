from domain.common.exceptions import BaseAppError, BaseDomainError
from litestar import Request, Response
from litestar.datastructures.state import State
from litestar.status_codes import HTTP_400_BAD_REQUEST


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


def domain_exception_handler(
    _request: Request[object, object, State],
    exc: BaseDomainError,
) -> Response[dict[str, str]]:
    status_code = HTTP_400_BAD_REQUEST

    return Response(
        content={
            'error': exc.__class__.__name__,
            'detail': exc.detail,
        },
        status_code=status_code,
    )


__all__ = ['app_exception_handler', 'domain_exception_handler']
