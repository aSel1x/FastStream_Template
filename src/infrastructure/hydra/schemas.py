from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from application.common.interfaces.acl.hydra_admin import HydraClient, HydraClientCreate

__all__ = (
    'HydraClient',
    'HydraClientCreate',
    'HydraClientRef',
    'HydraConsentRequest',
    'HydraIntrospection',
    'HydraLoginRequest',
    'HydraLogoutRequest',
    'HydraRedirect',
)


class _HydraModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra='ignore')


class HydraClientRef(_HydraModel):
    client_id: str = ''
    client_name: str = ''


class HydraLoginRequest(_HydraModel):
    challenge: str
    client: HydraClientRef = Field(default_factory=HydraClientRef)
    requested_scope: list[str] = Field(default_factory=list)
    requested_access_token_audience: list[str] = Field(default_factory=list)
    skip: bool = False
    subject: str | None = None
    session_id: str | None = None


class HydraConsentRequest(_HydraModel):
    challenge: str
    client: HydraClientRef = Field(default_factory=HydraClientRef)
    requested_scope: list[str] = Field(default_factory=list)
    requested_access_token_audience: list[str] = Field(default_factory=list)
    login_challenge: str | None = None
    login_session_id: str | None = None
    skip: bool = False
    context: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator('context', mode='before')
    @classmethod
    def _coerce_null_context(cls, value: dict[str, JsonValue] | None) -> dict[str, JsonValue]:
        """Hydra omits `context` on a login request accepted without one (e.g. the skip-login
        branch) and reports it back as JSON `null`, not an absent key."""
        return value if value is not None else {}


class HydraLogoutRequest(_HydraModel):
    challenge: str
    subject: str | None = None
    sid: str | None = None
    rp_initiated: bool = False


class HydraRedirect(_HydraModel):
    redirect_to: str


class HydraIntrospection(_HydraModel):
    active: bool = False
    #: Hydra reports refresh tokens as active too. `token_use` is the only field that tells
    #: an access token from a refresh token, so it decides whether a bearer is acceptable.
    token_use: str | None = None
    sub: str | None = None
    client_id: str | None = None
    scope: str = ''
    aud: list[str] = Field(default_factory=list)
    exp: int | None = None
    iat: int | None = None
    token_type: str | None = None
    ext: dict[str, JsonValue] = Field(default_factory=dict)
