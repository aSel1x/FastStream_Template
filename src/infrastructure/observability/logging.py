"""Structured JSON logging, correlated with the request and the trace.

The service previously configured logging not at all: whatever uvicorn set up, in plain text,
with no request id and no trace id. `request_id` already existed in a ContextVar and reached
exactly one place — the health response body — so nothing in a log line could be tied back to
the request that produced it.
"""

import json
import logging
import os
from datetime import UTC, datetime
from typing import ClassVar, final, override

from opentelemetry import trace

from domain.common.json_value import JsonValue
from infrastructure.observability.request_context import get_request_id

LOG_LEVEL_VAR = 'LOG_LEVEL'
LOG_FORMAT_VAR = 'LOG_FORMAT'

#: Attributes `logging` puts on every record; anything else was passed by the caller as
#: `extra=` and belongs in the structured output.
_RESERVED: frozenset[str] = frozenset(
    logging.LogRecord('', 0, '', 0, '', None, None).__dict__
) | frozenset({'message', 'asctime', 'taskName'})


def _as_json(value: object) -> JsonValue:
    """Whatever the caller passed as `extra=`, rendered so `json.dumps` cannot fail on it.

    Containers are stringified rather than walked: log fields are flat by convention, and
    recursing invites an unbounded structure on a hot path.
    """
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def _extra_fields(record: logging.LogRecord) -> dict[str, JsonValue]:
    """The caller's `extra=` fields, rendered as JSON values.

    `LogRecord.__dict__` is `dict[str, Any]`; `vars()` is narrowed to `object` here so every
    value has to go through `_as_json` rather than being trusted.
    """
    fields: dict[str, object] = {}
    fields.update(vars(record))
    return {key: _as_json(value) for key, value in fields.items() if key not in _RESERVED}


@final
class JsonFormatter(logging.Formatter):
    """One JSON object per line, with request and trace correlation."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, JsonValue] = {
            'timestamp': datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        request_id = get_request_id()
        if request_id:
            payload['request_id'] = request_id

        span = trace.get_current_span()
        context = span.get_span_context()
        if context.is_valid:
            payload['trace_id'] = format(context.trace_id, '032x')
            payload['span_id'] = format(context.span_id, '016x')

        if record.exc_info:
            payload['exception'] = self.formatException(record.exc_info)

        # Anything passed as `extra=` on the call site.
        payload.update(_extra_fields(record))

        return json.dumps(payload)


@final
class PlainFormatter(logging.Formatter):
    """Human-readable, for local development."""

    FORMAT: ClassVar[str] = '%(asctime)s %(levelname)-7s %(name)s: %(message)s'

    def __init__(self) -> None:
        super().__init__(fmt=self.FORMAT)


def configure_logging() -> None:
    """Install the root handler. Idempotent, so repeated app construction is harmless."""
    level = os.getenv(LOG_LEVEL_VAR, 'INFO').upper()
    use_json = os.getenv(LOG_FORMAT_VAR, 'json').lower() == 'json'

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if use_json else PlainFormatter())

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    # These are noisy at INFO and say nothing the access log does not.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('aio_pika').setLevel(logging.WARNING)
    logging.getLogger('aiormq').setLevel(logging.WARNING)
