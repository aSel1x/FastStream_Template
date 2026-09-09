from litestar import Request, Response
from litestar.datastructures.state import State
from litestar.status_codes import HTTP_502_BAD_GATEWAY

from application.common.exceptions import TooManyLoginAttemptsError
from domain.common.exceptions import BaseAppError, BaseDomainError
from infrastructure.hydra import HydraAdminError


def app_exception_handler(
    _request: Request[object, object, State],
    exc: BaseAppError,
) -> Response[dict[str, str]]:
    headers: dict[str, str] = {}
    # The limiter already computes when the caller may retry; without this the client has to
    # guess, and typically retries immediately.
    if isinstance(exc, TooManyLoginAttemptsError) and exc.retry_after_seconds is not None:
        headers['Retry-After'] = str(exc.retry_after_seconds)

    return Response(
        content={
            'error': exc.__class__.__name__,
            'detail': exc.detail,
        },
        status_code=exc.status,
        headers=headers,
    )


def domain_exception_handler(
    _request: Request[object, object, State],
    exc: BaseDomainError,
) -> Response[dict[str, str]]:
    return Response(
        content={
            'error': exc.__class__.__name__,
            'detail': exc.detail,
        },
        status_code=exc.status,
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
