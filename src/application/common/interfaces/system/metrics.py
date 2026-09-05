from typing import Protocol


class MetricsInterface(Protocol):
    """Counters the service publishes about itself.

    A port, not a direct Prometheus call: the application layer states *what* happened, and
    the adapter decides how it is recorded. It also keeps the use cases testable without a
    metrics registry, and keeps `application/` free of an infrastructure import.
    """

    def login_attempt(self, outcome: str, /) -> None:
        """One login attempt finished with `outcome` (success, bad_password, locked, ...)."""
        ...

    def two_factor_verification(self, outcome: str, kind: str, /) -> None:
        """A second factor was checked. `kind` distinguishes a TOTP code from a recovery code."""
        ...

    def session_created(self) -> None: ...

    def session_revoked(self, reason: str, /) -> None: ...

    def rate_limited(self, bucket: str, /) -> None:
        """A request was rejected by the limiter for `bucket`."""
        ...
