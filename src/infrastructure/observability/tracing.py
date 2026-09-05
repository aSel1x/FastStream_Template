from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from infrastructure.observability.config import ObservabilityConfig


def setup_tracing(config: ObservabilityConfig) -> TracerProvider | None:
    if not config.enabled:
        return None

    resource = Resource.create(
        {
            'service.name': config.service_name,
            'service.version': config.service_version,
        }
    )
    provider = TracerProvider(resource=resource)

    exporter = (
        OTLPSpanExporter(endpoint=config.otlp_endpoint)
        if config.otlp_endpoint
        else ConsoleSpanExporter()
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    SQLAlchemyInstrumentor().instrument()

    return provider
