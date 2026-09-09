from typing import ClassVar, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _HydraModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra='ignore')


class HydraClient(_HydraModel):
    client_id: str
    client_name: str = ''
    client_secret: str | None = None
    client_uri: str | None = None
    redirect_uris: list[str] = Field(default_factory=list)
    grant_types: list[str] = Field(default_factory=list)
    response_types: list[str] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list)
    token_endpoint_auth_method: str = 'client_secret_basic'  # noqa: S105 - an OAuth2 auth-method name, not a secret
    created_at: str | None = None

    @field_validator('scope', mode='before')
    @classmethod
    def _split_scope(cls, value: object) -> object:
        if isinstance(value, str):
            return value.split()
        return value


class HydraClientCreate(_HydraModel):
    client_name: str
    redirect_uris: list[str]
    grant_types: list[str]
    response_types: list[str]
    scope: list[str]
    token_endpoint_auth_method: str
    client_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


class ProviderClientNotFoundError(Exception):
    """The upstream authorization server has no such client.

    Declared on the port rather than reusing the Hydra client's own exception: catching an
    infrastructure class in a use case is the dependency rule pointing the wrong way, and it
    would make swapping the provider a change to the application layer.
    """


class HydraAdminClientInterface(Protocol):
    async def create_client(self, data: HydraClientCreate) -> HydraClient: ...

    async def list_clients(self, page_size: int = 100) -> list[HydraClient]: ...

    async def delete_client(self, client_id: str) -> None: ...

    async def rotate_client_secret(self, client_id: str) -> HydraClient: ...

    async def revoke_login_sessions(self, subject: str) -> None: ...

    async def revoke_consent_sessions(self, subject: str) -> None: ...
