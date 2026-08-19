from dataclasses import dataclass, field
from os import getenv
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


@dataclass
class SeedClientConfig:
    client_id: str
    client_name: str
    client_secret: str = ''
    redirect_uris: tuple[str, ...] = field(default_factory=tuple)
    grant_types: tuple[str, ...] = ('authorization_code',)
    scopes: tuple[str, ...] = ('openid', 'profile', 'email')
    is_confidential: bool = False


class _SeedClientWire(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra='ignore')

    client_id: str = ''
    client_name: str = ''
    client_secret: str = ''
    redirect_uris: list[str] = Field(default_factory=list)
    grant_types: list[str] = Field(default_factory=lambda: ['authorization_code'])
    scopes: list[str] = Field(default_factory=lambda: ['openid', 'profile', 'email'])
    is_confidential: bool = False


_seed_clients_adapter = TypeAdapter[list[_SeedClientWire] | _SeedClientWire](
    list[_SeedClientWire] | _SeedClientWire
)


def _to_seed_client_config(wire: _SeedClientWire) -> SeedClientConfig:
    return SeedClientConfig(
        client_id=wire.client_id,
        client_name=wire.client_name or wire.client_id,
        client_secret=wire.client_secret,
        redirect_uris=tuple(wire.redirect_uris),
        grant_types=tuple(wire.grant_types),
        scopes=tuple(wire.scopes),
        is_confidential=wire.is_confidential,
    )


@dataclass
class OAuthSeedConfig:
    clients: tuple[SeedClientConfig, ...] = field(default_factory=tuple)

    @classmethod
    def from_environ(cls) -> 'OAuthSeedConfig':
        raw = getenv('OAUTH_SEED_CLIENTS', '')
        if not raw:
            return cls()

        try:
            parsed = _seed_clients_adapter.validate_json(raw)
        except ValidationError:
            return cls()

        wire_clients = parsed if isinstance(parsed, list) else [parsed]
        return cls(clients=tuple(_to_seed_client_config(wire) for wire in wire_clients))
