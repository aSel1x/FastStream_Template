from typing import final, override

from application.common.interfaces.system.metrics import MetricsInterface
from infrastructure.observability.metrics import (
    LOGIN_ATTEMPTS,
    RATE_LIMIT_REJECTIONS,
    SESSIONS_CREATED,
    SESSIONS_REVOKED,
    TWO_FACTOR_VERIFICATIONS,
)


@final
class PrometheusMetrics(MetricsInterface):
    @override
    def login_attempt(self, outcome: str, /) -> None:
        LOGIN_ATTEMPTS.labels(outcome=outcome).inc()

    @override
    def two_factor_verification(self, outcome: str, kind: str, /) -> None:
        TWO_FACTOR_VERIFICATIONS.labels(outcome=outcome, kind=kind).inc()

    @override
    def session_created(self) -> None:
        SESSIONS_CREATED.inc()

    @override
    def session_revoked(self, reason: str, /) -> None:
        SESSIONS_REVOKED.labels(reason=reason).inc()

    @override
    def rate_limited(self, bucket: str, /) -> None:
        RATE_LIMIT_REJECTIONS.labels(bucket=bucket).inc()


@final
class NullMetrics(MetricsInterface):
    """Records nothing. Keeps tests and the in-memory wiring free of a registry."""

    @override
    def login_attempt(self, outcome: str, /) -> None: ...

    @override
    def two_factor_verification(self, outcome: str, kind: str, /) -> None: ...

    @override
    def session_created(self) -> None: ...

    @override
    def session_revoked(self, reason: str, /) -> None: ...

    @override
    def rate_limited(self, bucket: str, /) -> None: ...
