from dataclasses import dataclass
from os import getenv

from application.common.exceptions import ConfigurationError


@dataclass
class HydraConfig:
    admin_url: str = 'http://localhost:4445'
    public_url: str = 'http://localhost:4444'
    login_remember_seconds: int = 3600
    consent_remember_seconds: int = 60 * 60 * 24 * 30
    introspection_cache_ttl_seconds: int = 30
    introspection_negative_cache_ttl_seconds: int = 10
    request_timeout_seconds: float = 5.0

    @classmethod
    def from_environ(cls) -> HydraConfig:
        admin_url = getenv('HYDRA_ADMIN_URL', 'http://localhost:4445')
        public_url = getenv('HYDRA_PUBLIC_URL', 'http://localhost:4444')

        if getenv('ENV', 'development') == 'production':
            if not getenv('HYDRA_ADMIN_URL'):
                raise ConfigurationError('HYDRA_ADMIN_URL must be set in production')
            if not getenv('HYDRA_PUBLIC_URL'):
                raise ConfigurationError('HYDRA_PUBLIC_URL must be set in production')

        return cls(
            admin_url=admin_url,
            public_url=public_url,
            login_remember_seconds=int(getenv('HYDRA_LOGIN_REMEMBER_SECONDS', '3600')),
            consent_remember_seconds=int(
                getenv('HYDRA_CONSENT_REMEMBER_SECONDS', str(60 * 60 * 24 * 30))
            ),
            introspection_cache_ttl_seconds=int(
                getenv('HYDRA_INTROSPECTION_CACHE_TTL_SECONDS', '30')
            ),
            introspection_negative_cache_ttl_seconds=int(
                getenv('HYDRA_INTROSPECTION_NEGATIVE_CACHE_TTL_SECONDS', '10'),
            ),
            request_timeout_seconds=float(getenv('HYDRA_REQUEST_TIMEOUT_SECONDS', '5.0')),
        )
