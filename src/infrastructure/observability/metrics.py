"""Prometheus metrics for the things an identity service is actually asked about.

Tracing answers "where did this request spend its time"; it does not answer "how many logins
failed in the last hour" or "how far behind is the outbox". Those need counters.
"""

from typing import Final

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

CONTENT_TYPE: Final = 'text/plain; version=0.0.4; charset=utf-8'

REGISTRY: Final = CollectorRegistry(auto_describe=True)

LOGIN_ATTEMPTS: Final = Counter(
    'identity_login_attempts_total',
    'Login attempts by outcome.',
    labelnames=('outcome',),
    registry=REGISTRY,
)

TWO_FACTOR_VERIFICATIONS: Final = Counter(
    'identity_two_factor_verifications_total',
    'Second-factor verifications by outcome and kind of code.',
    labelnames=('outcome', 'kind'),
    registry=REGISTRY,
)

SESSIONS_CREATED: Final = Counter(
    'identity_sessions_created_total',
    'Sessions created.',
    registry=REGISTRY,
)

SESSIONS_REVOKED: Final = Counter(
    'identity_sessions_revoked_total',
    'Sessions revoked, by what triggered it.',
    labelnames=('reason',),
    registry=REGISTRY,
)

RATE_LIMIT_REJECTIONS: Final = Counter(
    'identity_rate_limit_rejections_total',
    'Requests rejected by a rate limiter, by bucket.',
    labelnames=('bucket',),
    registry=REGISTRY,
)

OUTBOX_PENDING: Final = Gauge(
    'identity_outbox_pending_events',
    'Events waiting to be relayed.',
    registry=REGISTRY,
)

OUTBOX_OLDEST_AGE_SECONDS: Final = Gauge(
    'identity_outbox_oldest_pending_age_seconds',
    'Age of the oldest unrelayed event. The number that tells you the relay has stalled.',
    registry=REGISTRY,
)

OUTBOX_FAILED: Final = Gauge(
    'identity_outbox_failed_events',
    'Events that exhausted their retries and were dead-lettered.',
    registry=REGISTRY,
)

OUTBOX_RELAY_SECONDS: Final = Histogram(
    'identity_outbox_relay_seconds',
    'Time to relay one batch.',
    registry=REGISTRY,
)


def render() -> bytes:
    return generate_latest(REGISTRY)
