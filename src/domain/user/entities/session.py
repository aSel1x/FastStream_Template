from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Self, override
from uuid import UUID, uuid4

from domain.common.entity import BaseEntity
from domain.common.value_object import BaseValueObject
from domain.common.event_dispatcher import DomainEventDispatcher
from domain.user.events import SessionCreatedEvent, SessionRevokedEvent, TokenRefreshedEvent
from domain.user.value_objects import TokenHash, UserID


@dataclass(frozen=True)
class DeviceInfo(BaseValueObject):
    @override
    def _validate(self) -> None:
        pass
    user_agent: str | None = None
    ip_address: str | None = None
    device_name: str | None = None
    browser: str | None = None
    os: str | None = None
    is_mobile: bool = False

    def with_user_agent(self, user_agent: str | None) -> 'DeviceInfo':
        return DeviceInfo(
            user_agent=user_agent,
            ip_address=self.ip_address,
            device_name=self.device_name,
            browser=self.browser,
            os=self.os,
            is_mobile=self.is_mobile,
        )

    def with_ip(self, ip_address: str | None) -> 'DeviceInfo':
        return DeviceInfo(
            user_agent=self.user_agent,
            ip_address=ip_address,
            device_name=self.device_name,
            browser=self.browser,
            os=self.os,
            is_mobile=self.is_mobile,
        )


@dataclass(frozen=True, eq=False)
class RefreshToken(BaseEntity):
    token_hash: TokenHash
    id: UUID = field(default_factory=uuid4)
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_revoked: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @override
    def _identity(self) -> object:
        return self.id

    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at

    def is_valid(self) -> bool:
        return not self.is_revoked and not self.is_expired()

    def revoked(self) -> 'RefreshToken':
        return RefreshToken(
            id=self.id,
            token_hash=self.token_hash,
            expires_at=self.expires_at,
            is_revoked=True,
            created_at=self.created_at,
        )


@dataclass(frozen=True, kw_only=True, eq=False)
class SessionAggregate(DomainEventDispatcher, BaseEntity):
    session_id: UUID
    user_id: UserID
    device_info: DeviceInfo
    created_at: datetime
    expires_at: datetime
    is_revoked: bool = False
    refresh_tokens: tuple[RefreshToken, ...] = field(default_factory=tuple)

    @override
    def _identity(self) -> object:
        return self.session_id

    @classmethod
    def create(
        cls,
        user_id: UserID,
        device_info: DeviceInfo,
        session_expire_seconds: int = 60 * 60 * 24 * 30,
    ) -> Self:
        now = datetime.now(UTC)
        session = cls(
            session_id=uuid4(),
            user_id=user_id,
            device_info=device_info,
            created_at=now,
            expires_at=now + timedelta(seconds=session_expire_seconds),
        )
        session._record_event(SessionCreatedEvent(
            session_id=session.session_id,
            user_id=session.user_id.to_raw(),
            device_info={
                'user_agent': device_info.user_agent,
                'ip_address': device_info.ip_address,
                'device_name': device_info.device_name,
            },
        ))
        return session

    def is_expired(self) -> bool:
        return datetime.now(UTC) >= self.expires_at

    def is_valid(self) -> bool:
        return not self.is_revoked and not self.is_expired()

    def add_refresh_token(self, token: RefreshToken) -> Self:
        return self._with(refresh_tokens=self.refresh_tokens + (token,))

    def find_valid_refresh_token(self, token_hash: TokenHash) -> RefreshToken | None:
        for token in self.refresh_tokens:
            if token.token_hash == token_hash and token.is_valid():
                return token
        return None

    def revoke_token(self, token_id: UUID) -> Self:
        new_tokens = tuple(
            t.revoked() if t.id == token_id else t
            for t in self.refresh_tokens
        )
        return self._with(refresh_tokens=new_tokens)

    def revoke(self) -> Self:
        session = self._with(
            is_revoked=True,
            refresh_tokens=tuple(t.revoked() for t in self.refresh_tokens),
        )
        session._record_event(SessionRevokedEvent(
            session_id=self.session_id,
            user_id=self.user_id.to_raw(),
        ))
        return session

    def refresh(self, new_expire_seconds: int = 60 * 60 * 24 * 30) -> Self:
        now = datetime.now(UTC)
        session = self._with(expires_at=now + timedelta(seconds=new_expire_seconds))
        session._record_event(TokenRefreshedEvent(
            session_id=self.session_id,
            user_id=self.user_id.to_raw(),
        ))
        return session