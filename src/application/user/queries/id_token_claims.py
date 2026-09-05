from dataclasses import dataclass, field
from typing import final
from uuid import UUID

from domain.common.json_value import JsonValue
from domain.user.interfaces.persistence.readers import UserReader
from domain.user.value_objects import UserID

SCOPE_PROFILE = 'profile'
SCOPE_EMAIL = 'email'


@dataclass
class ConsentClaimsInput:
    user_id: UUID | None
    session_id: str | None
    granted_scopes: list[str]


@dataclass
class ConsentClaims:
    """What the relying party will see in the tokens Hydra issues."""

    id_token: dict[str, JsonValue] = field(default_factory=dict)
    access_token: dict[str, JsonValue] = field(default_factory=dict)


@final
class BuildConsentClaimsUseCase:
    """Decides which of the user's attributes each granted scope discloses.

    This is the substance of consent — a scope is a promise about what the client will and
    will not receive — so it belongs in the application layer rather than inline in the HTTP
    controller, where it could not be tested without Litestar and Hydra.
    """

    def __init__(self, user_reader: UserReader) -> None:
        self._user_reader = user_reader

    async def __call__(self, data: ConsentClaimsInput) -> ConsentClaims:
        claims = ConsentClaims()

        if data.session_id:
            # Lets the resource server tie an access token back to a revocable session.
            claims.access_token['session_id'] = data.session_id

        if data.user_id is None:
            return claims

        user = await self._user_reader.get_by_id(UserID(data.user_id))
        if user is None:
            return claims

        if SCOPE_PROFILE in data.granted_scopes:
            claims.id_token['preferred_username'] = user.username
        if SCOPE_EMAIL in data.granted_scopes:
            claims.id_token['email'] = user.email
            claims.id_token['email_verified'] = user.is_email_verified

        return claims
