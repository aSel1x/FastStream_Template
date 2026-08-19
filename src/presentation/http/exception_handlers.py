from domain.common.exceptions import BaseAppError, BaseDomainError
from infrastructure.hydra import HydraAdminError
from litestar import Request, Response
from litestar.datastructures.state import State
from litestar.status_codes import HTTP_400_BAD_REQUEST, HTTP_502_BAD_GATEWAY


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
    status_code = getattr(exc, 'status', HTTP_400_BAD_REQUEST)

    return Response(
        content={
            'error': exc.__class__.__name__,
            'detail': exc.detail,
        },
        status_code=status_code,
    )


def hydra_admin_error_handler(
    _request: Request[object, object, State],
    exc: HydraAdminError,
) -> Response[dict[str, str]]:
    # Forward Hydra's own 4xx as-is (the caller's request was invalid); collapse
    # anything else (Hydra down, 5xx) to a 502 so we don't leak upstream internals.
    status_code = exc.status_code if 400 <= exc.status_code < 500 else HTTP_502_BAD_GATEWAY

    return Response(
        content={
            'error': exc.__class__.__name__,
            'detail': str(exc),
        },
        status_code=status_code,
    )


__all__ = ['app_exception_handler', 'domain_exception_handler', 'hydra_admin_error_handler']
