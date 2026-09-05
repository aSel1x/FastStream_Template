from dataclasses import dataclass
from os import getenv


@dataclass
class EmailConfig:
    host: str = 'localhost'
    port: int = 587
    username: str = ''
    password: str = ''
    use_tls: bool = True
    from_addr: str = 'noreply@example.com'
    app_base_url: str = 'http://localhost:8000'

    @classmethod
    def from_environ(cls) -> EmailConfig:
        return cls(
            host=getenv('SMTP_HOST', 'localhost'),
            port=int(getenv('SMTP_PORT', '587')),
            username=getenv('SMTP_USERNAME', ''),
            password=getenv('SMTP_PASSWORD', ''),
            use_tls=getenv('SMTP_USE_TLS', 'true').lower() == 'true',
            from_addr=getenv('SMTP_FROM_ADDR', 'noreply@example.com'),
            app_base_url=getenv('APP_BASE_URL', 'http://localhost:8000'),
        )
