from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from application.user.commands.change_password import ChangePasswordInput, ChangePasswordUseCase
from application.user.commands.create_user import CreateUserInput, CreateUserUseCase
from application.user.commands.delete_me import DeleteMeUseCase
from application.user.commands.login import LoginInput, LoginUseCase
from application.user.commands.refresh_token import RefreshTokenInput, RefreshTokenUseCase
from application.user.commands.manage_2fa import (
    Enable2FAUseCase,
    Disable2FAUseCase,
    Verify2FAInput,
    Verify2FAUseCase,
)
from application.user.commands.manage_sessions import RevokeAllSessionsUseCase, RevokeSessionUseCase
from application.user.commands.reset_password import RequestPasswordResetInput, ResetPasswordInput, RequestPasswordResetUseCase, ResetPasswordUseCase
from application.user.commands.update_profile import UpdateProfileInput, UpdateProfileUseCase
from application.user.commands.verify_email import VerifyEmailInput, VerifyEmailUseCase
from application.user.queries.get_me import GetMeUseCase
from application.user.queries.manage_sessions import GetUserSessionsUseCase
from litestar import Controller, delete, get, patch, post
from litestar.connection import Request
from litestar.datastructures.state import State
from litestar.params import Parameter
from litestar.security.jwt import Token
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from pydantic import BaseModel
from dishka import FromDishka
from dishka.integrations.litestar import inject

from infrastructure.idempotency import IdempotencyStore
from presentation.http.guards import require_scope
from presentation.http.middleware.request_id import get_request_id
from presentation.http.security import UserSecuritySchema


class RegisterRequestSchema(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginRequestSchema(BaseModel):
    password: str
    username: str | None = None
    email: str | None = None


class LoginResponseSchema(BaseModel):
    user_id: str
    session_id: str
    refresh_token: str | None = None
    requires_two_factor: bool = False


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str


class RefreshTokenResponseSchema(BaseModel):
    user_id: str
    session_id: str
    expires_at: str


class ChangePasswordRequestSchema(BaseModel):
    old_password: str
    new_password: str


class UserProfileResponseSchema(BaseModel):
    user_id: str
    username: str
    email: str | None = None
    is_email_verified: bool = False
    is_locked: bool = False
    has_two_factor: bool = False


class UserProfileUpdatedRequestSchema(BaseModel):
    username: str | None = None
    email: str | None = None


class VerifyEmailRequestSchema(BaseModel):
    token: str


class RequestPasswordResetSchema(BaseModel):
    email: str


class ResetPasswordSchema(BaseModel):
    user_id: str
    token: str
    new_password: str


class EnableTwoFactorResponseSchema(BaseModel):
    secret: str
    backup_codes: list[str]
    provisioning_uri: str


class Disable2FARequestSchema(BaseModel):
    current_password: str


class TwoFactorVerifyRequestSchema(BaseModel):
    code: str


class TwoFactorVerifyResponseSchema(BaseModel):
    success: bool


class SessionResponseSchema(BaseModel):
    session_id: str
    created_at: str
    expires_at: str
    is_valid: bool
    device: dict[str, str | None]


class SessionsPageResponseSchema(BaseModel):
    sessions: list[SessionResponseSchema]
    total: int
    limit: int
    offset: int
    has_more: bool


class HealthResponseSchema(BaseModel):
    status: str
    version: str
    request_id: str


class UserController(Controller):
    path: str = '/v1/users'

    @post(
        '/register',
        status_code=HTTP_201_CREATED,
        summary='Register new user',
        tags=['auth'],
    )
    @inject
    async def register(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: RegisterRequestSchema,
        use_case: FromDishka[CreateUserUseCase],
        idempotency: FromDishka[IdempotencyStore],
        idempotency_key: Annotated[str | None, Parameter(header='Idempotency-Key')] = None,
    ) -> UUID:
        client_host = request.client.host if request.client else 'unknown'

        if idempotency_key:
            cached = await idempotency.get_cached_response('register', client_host, idempotency_key)
            cached_user_id = cached.get('user_id') if cached is not None else None
            if isinstance(cached_user_id, str):
                return UUID(cached_user_id)

        user_id = await use_case(CreateUserInput(
            username=data.username,
            password=data.password,
            email=data.email,
            ip_address=request.client.host if request.client else None,
        ))

        if idempotency_key:
            await idempotency.cache_response(
                'register', client_host, idempotency_key, {'user_id': str(user_id)},
            )

        return user_id

    @post(
        '/login',
        status_code=HTTP_200_OK,
        summary='Authenticate user (credential check only — OAuth2 tokens are issued by Ory Hydra)',
        tags=['auth'],
    )
    @inject
    async def login(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: LoginRequestSchema,
        use_case: FromDishka[LoginUseCase],
    ) -> LoginResponseSchema:
        result = await use_case(LoginInput(
            password=data.password,
            username=data.username,
            email=data.email,
            user_agent=request.headers.get('user-agent'),
            ip_address=request.client.host if request.client else None,
        ))
        return LoginResponseSchema(
            user_id=str(result.user_id),
            session_id=result.session_id,
            refresh_token=result.refresh_token,
            requires_two_factor=result.requires_two_factor,
        )

    @get(
        '/me',
        status_code=HTTP_200_OK,
        summary='Get current user profile',
        tags=['users'],
        guards=[require_scope('profile')],
    )
    @inject
    async def get_me(
        self,
        request: Request[UserSecuritySchema, Token, State],
        use_case: FromDishka[GetMeUseCase],
    ) -> UserProfileResponseSchema:
        result = await use_case(request.user.user_id)
        return UserProfileResponseSchema(
            user_id=result.user_id,
            username=result.username,
            email=result.email,
            is_email_verified=result.is_email_verified,
            is_locked=result.is_locked,
            has_two_factor=result.has_two_factor,
        )

    @patch(
        '/me',
        status_code=HTTP_200_OK,
        summary='Update current user profile',
        tags=['users'],
        guards=[require_scope('profile')],
    )
    @inject
    async def update_profile(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: UserProfileUpdatedRequestSchema,
        use_case: FromDishka[UpdateProfileUseCase],
    ) -> UserProfileResponseSchema:
        result = await use_case(UpdateProfileInput(
            user_id=request.user.user_id,
            username=data.username,
            email=data.email,
        ))
        return UserProfileResponseSchema(
            user_id=str(request.user.user_id),
            username=result.username,
            email=result.email,
            is_email_verified=result.is_email_verified,
            is_locked=result.is_locked,
            has_two_factor=result.has_two_factor,
        )

    @delete(
        '/me',
        status_code=HTTP_200_OK,
        summary='Delete current user account',
        tags=['users'],
    )
    @inject
    async def delete_me(
        self,
        request: Request[UserSecuritySchema, Token, State],
        use_case: FromDishka[DeleteMeUseCase],
    ) -> None:
        await use_case(request.user.user_id)

    @post(
        '/me/password',
        status_code=HTTP_200_OK,
        summary="Change current user's password",
        tags=['users'],
    )
    @inject
    async def change_password(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: ChangePasswordRequestSchema,
        use_case: FromDishka[ChangePasswordUseCase],
    ) -> dict[str, bool]:
        result = await use_case(ChangePasswordInput(
            user_id=request.user.user_id,
            old_password=data.old_password,
            new_password=data.new_password,
        ))
        return {'success': result.success}


class AuthController(Controller):
    path: str = '/v1/auth'

    @post(
        '/refresh',
        status_code=HTTP_200_OK,
        summary='Exchange a refresh token for a renewed session',
        tags=['auth'],
    )
    @inject
    async def refresh(
        self,
        data: RefreshTokenRequestSchema,
        use_case: FromDishka[RefreshTokenUseCase],
    ) -> RefreshTokenResponseSchema:
        result = await use_case(RefreshTokenInput(refresh_token=data.refresh_token))
        return RefreshTokenResponseSchema(
            user_id=str(result.user_id),
            session_id=result.session_id,
            expires_at=result.expires_at,
        )

    @post(
        '/verify-email',
        status_code=HTTP_200_OK,
        summary='Verify email',
        tags=['auth'],
    )
    @inject
    async def verify_email(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: VerifyEmailRequestSchema,
        use_case: FromDishka[VerifyEmailUseCase],
    ) -> dict[str, bool]:
        result = await use_case(VerifyEmailInput(
            user_id=str(request.user.user_id),
            token=data.token,
        ))
        return {'success': result.success}

    @post(
        '/request-password-reset',
        status_code=HTTP_200_OK,
        summary='Request password reset',
        tags=['auth'],
    )
    @inject
    async def request_password_reset(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: RequestPasswordResetSchema,
        use_case: FromDishka[RequestPasswordResetUseCase],
    ) -> dict[str, bool]:
        result = await use_case(RequestPasswordResetInput(
            email=data.email,
            ip_address=request.client.host if request.client else None,
        ))
        return {'success': result.success}

    @post(
        '/reset-password',
        status_code=HTTP_200_OK,
        summary='Reset password',
        tags=['auth'],
    )
    @inject
    async def reset_password(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: ResetPasswordSchema,
        use_case: FromDishka[ResetPasswordUseCase],
    ) -> dict[str, bool]:
        result = await use_case(ResetPasswordInput(
            user_id=data.user_id,
            token=data.token,
            new_password=data.new_password,
            ip_address=request.client.host if request.client else None,
        ))
        return {'success': result.success}

    @post(
        '/2fa/enable',
        status_code=HTTP_200_OK,
        summary='Enable two-factor authentication',
        tags=['2fa'],
    )
    @inject
    async def enable_2fa(
        self,
        request: Request[UserSecuritySchema, Token, State],
        use_case: FromDishka[Enable2FAUseCase],
    ) -> EnableTwoFactorResponseSchema:
        result = await use_case(request.user.user_id)
        return EnableTwoFactorResponseSchema(
            secret=result.secret,
            backup_codes=result.backup_codes,
            provisioning_uri=result.provisioning_uri,
        )

    @post(
        '/2fa/disable',
        status_code=HTTP_200_OK,
        summary='Disable two-factor authentication',
        tags=['2fa'],
    )
    @inject
    async def disable_2fa(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: Disable2FARequestSchema,
        use_case: FromDishka[Disable2FAUseCase],
    ) -> dict[str, bool]:
        await use_case(request.user.user_id, data.current_password)
        return {'success': True}

    @post(
        '/2fa/verify',
        status_code=HTTP_200_OK,
        summary='Verify two-factor code',
        tags=['2fa'],
    )
    @inject
    async def verify_2fa(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: TwoFactorVerifyRequestSchema,
        use_case: FromDishka[Verify2FAUseCase],
    ) -> TwoFactorVerifyResponseSchema:
        result = await use_case(request.user.user_id, Verify2FAInput(code=data.code))
        return TwoFactorVerifyResponseSchema(success=result.success)


class SessionController(Controller):
    path: str = '/v1/sessions'

    @get(
        '/',
        status_code=HTTP_200_OK,
        summary='Get user sessions',
        tags=['sessions'],
    )
    @inject
    async def get_sessions(
        self,
        request: Request[UserSecuritySchema, Token, State],
        use_case: FromDishka[GetUserSessionsUseCase],
    ) -> SessionsPageResponseSchema:
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        result = await use_case(request.user.user_id, limit=limit, offset=offset)
        now = datetime.now(UTC)
        return SessionsPageResponseSchema(
            sessions=[
                SessionResponseSchema(
                    session_id=str(s.session_id),
                    created_at=s.created_at.isoformat(),
                    expires_at=s.expires_at.isoformat(),
                    is_valid=not s.is_revoked and now < s.expires_at,
                    device={
                        'user_agent': s.device_info.user_agent,
                        'ip_address': s.device_info.ip_address,
                        'device_name': s.device_info.device_name,
                    },
                )
                for s in result.sessions
            ],
            total=result.total,
            limit=result.limit,
            offset=result.offset,
            has_more=result.has_more,
        )

    @delete(
        '/{session_id:str}',
        status_code=HTTP_200_OK,
        summary='Revoke session',
        tags=['sessions'],
    )
    @inject
    async def revoke_session(
        self,
        request: Request[UserSecuritySchema, Token, State],
        session_id: str,
        use_case: FromDishka[RevokeSessionUseCase],
    ) -> None:
        await use_case(request.user.user_id, session_id)

    @delete(
        '/',
        status_code=HTTP_200_OK,
        summary='Revoke all sessions',
        tags=['sessions'],
    )
    @inject
    async def revoke_all_sessions(
        self,
        request: Request[UserSecuritySchema, Token, State],
        use_case: FromDishka[RevokeAllSessionsUseCase],
    ) -> None:
        await use_case(request.user.user_id)


class HealthController(Controller):
    path: str = '/health'

    @get(
        '/',
        summary='Health check',
        tags=['health'],
    )
    async def health(self) -> HealthResponseSchema:
        return HealthResponseSchema(
            status='healthy',
            version='1.0.0',
            request_id=get_request_id() or 'unknown',
        )
