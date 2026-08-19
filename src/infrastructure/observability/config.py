from dataclasses import dataclass
from os import getenv


@dataclass
class ObservabilityConfig:
    enabled: bool = False
    service_name: str = 'backend-template'
    service_version: str = '1.0.0'
    otlp_endpoint: str | None = None

    @classmethod
    def from_environ(cls) -> 'ObservabilityConfig':
        return cls(
            enabled=getenv('OTEL_ENABLED', 'false').lower() == 'true',
            service_name=getenv('OTEL_SERVICE_NAME', 'backend-template'),
            service_version=getenv('OTEL_SERVICE_VERSION', '1.0.0'),
            otlp_endpoint=getenv('OTEL_EXPORTER_OTLP_ENDPOINT') or None,
        )
