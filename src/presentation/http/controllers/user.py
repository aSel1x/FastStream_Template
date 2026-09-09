from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, delete, get, patch, post
from litestar.connection import Request
from litestar.datastructures.state import State
from litestar.params import FromPath, FromQuery, HeaderParameter, Parameter
from litestar.response import Template
from litestar.security.jwt import Token
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from pydantic import BaseModel

from application.user.commands.change_password import ChangePasswordInput, ChangePasswordUseCase
from application.user.commands.complete_two_factor import (
    CompleteTwoFactorInput,
    CompleteTwoFactorUseCase,
)
from application.user.commands.create_user import CreateUserInput, CreateUserUseCase
from application.user.commands.delete_me import DeleteMeUseCase
from application.user.commands.login import LoginInput, LoginUseCase
from application.user.commands.manage_2fa import (
    Confirm2FAInput,
    Confirm2FAUseCase,
    Disable2FAUseCase,
    Enable2FAUseCase,
    Verify2FAInput,
    Verify2FAUseCase,
)
from application.user.commands.manage_sessions import RevokeAllSessionsUseCase, RevokeSessionUseCase
from application.user.commands.refresh_token import RefreshTokenInput, RefreshTokenUseCase
from application.user.commands.reset_password import (
    RequestPasswordResetInput,
    RequestPasswordResetUseCase,
    ResetPasswordInput,
    ResetPasswordUseCase,
)
from application.user.commands.update_profile import UpdateProfileInput, UpdateProfileUseCase
from application.user.commands.verify_email import VerifyEmailInput, VerifyEmailUseCase
from application.user.queries.get_me import GetMeUseCase
from application.user.queries.manage_sessions import GetUserSessionsUseCase
from domain.common.exceptions import BaseDomainError
from infrastructure.idempotency import IdempotencyStore
from presentation.http.client_ip import client_ip, client_ip_or_unknown
from presentation.http.guards import (
    SCOPE_ACCOUNT_WRITE,
    SCOPE_PROFILE,
    SCOPE_SESSIONS_WRITE,
    require_scope,
)
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
    """Either a session, or a two-factor challenge — never both."""

    user_id: str
    session_id: str | None = None
    refresh_token: str | None = None
    requires_two_factor: bool = False
    #: Present only when `requires_two_factor` is set. Exchange it, with a code, at
    #: `POST /v1/auth/2fa/challenge` to obtain the session.
    challenge_token: str | None = None


class TwoFactorChallengeRequestSchema(BaseModel):
    challenge_token: str
    code: str


class TwoFactorChallengeResponseSchema(BaseModel):
    user_id: str
    session_id: str
    refresh_token: str


class RefreshTokenRequestSchema(BaseModel):
    refresh_token: str


class RefreshTokenResponseSchema(BaseModel):
    user_id: str
    session_id: str
    expires_at: str
    #: Rotated on every refresh. The token that was presented is now revoked; replaying it
    #: revokes the whole session.
    refresh_token: str


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


def _result_context(message: str = '', error: str = '') -> dict[str, str]:
    return {'message': message, 'error': error}


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
        idempotency_key: Annotated[str | None, HeaderParameter(name='Idempotency-Key')] = None,
    ) -> UUID:
        client_host = client_ip_or_unknown(request)

        if idempotency_key:
            cached = await idempotency.get_cached_response('register', client_host, idempotency_key)
            cached_user_id = cached.get('user_id') if cached is not None else None
            if isinstance(cached_user_id, str):
                return UUID(cached_user_id)

        user_id = await use_case(
            CreateUserInput(
                username=data.username,
                password=data.password,
                email=data.email,
                ip_address=client_ip(request),
            )
        )

        if idempotency_key:
            await idempotency.cache_response(
                'register',
                client_host,
                idempotency_key,
                {'user_id': str(user_id)},
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
        result = await use_case(
            LoginInput(
                password=data.password,
                username=data.username,
                email=data.email,
                user_agent=request.headers.get('user-agent'),
                ip_address=client_ip(request),
            )
        )
        return LoginResponseSchema(
            user_id=str(result.user_id),
            session_id=result.session_id,
            refresh_token=result.refresh_token,
            requires_two_factor=result.requires_two_factor,
            challenge_token=result.challenge_token,
        )

    @get(
        '/me',
        status_code=HTTP_200_OK,
        summary='Get current user profile',
        tags=['users'],
        guards=[require_scope(SCOPE_PROFILE)],
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
        guards=[require_scope(SCOPE_PROFILE)],
    )
    @inject
    async def update_profile(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: UserProfileUpdatedRequestSchema,
        use_case: FromDishka[UpdateProfileUseCase],
    ) -> UserProfileResponseSchema:
        result = await use_case(
            UpdateProfileInput(
                user_id=request.user.user_id,
                username=data.username,
                email=data.email,
            )
        )
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
        guards=[require_scope(SCOPE_ACCOUNT_WRITE)],
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
        guards=[require_scope(SCOPE_ACCOUNT_WRITE)],
    )
    @inject
    async def change_password(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: ChangePasswordRequestSchema,
        use_case: FromDishka[ChangePasswordUseCase],
    ) -> dict[str, bool]:
        result = await use_case(
            ChangePasswordInput(
                user_id=request.user.user_id,
                old_password=data.old_password,
                new_password=data.new_password,
            )
        )
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
            refresh_token=result.refresh_token,
        )

    @post(
        '/2fa/challenge',
        status_code=HTTP_200_OK,
        summary='Complete a two-factor challenge and receive the session',
        description=(
            'The second half of login for accounts with 2FA. Unauthenticated: the challenge '
            'token issued by /v1/users/login is the credential. Accepts a TOTP code or a '
            'recovery code.'
        ),
        tags=['2fa'],
    )
    @inject
    async def complete_two_factor(
        self,
        data: TwoFactorChallengeRequestSchema,
        use_case: FromDishka[CompleteTwoFactorUseCase],
    ) -> TwoFactorChallengeResponseSchema:
        result = await use_case(
            CompleteTwoFactorInput(challenge_token=data.challenge_token, code=data.code)
        )
        return TwoFactorChallengeResponseSchema(
            user_id=str(result.user_id),
            session_id=result.session_id,
            refresh_token=result.refresh_token,
        )

    @post(
        '/verify-email',
        status_code=HTTP_200_OK,
        summary='Verify email (API)',
        description='The token identifies the user, so no authentication is required.',
        tags=['auth'],
    )
    @inject
    async def verify_email(
        self,
        data: VerifyEmailRequestSchema,
        use_case: FromDishka[VerifyEmailUseCase],
    ) -> dict[str, bool]:
        result = await use_case(VerifyEmailInput(token=data.token))
        return {'success': result.success}

    @get(
        '/verify-email',
        status_code=HTTP_200_OK,
        summary='Verify email (link from the email)',
        description='The landing page the verification email links to.',
        tags=['auth'],
        include_in_schema=False,
    )
    @inject
    async def verify_email_landing(
        self,
        token: FromQuery[str],
        use_case: FromDishka[VerifyEmailUseCase],
    ) -> Template:
        try:
            _ = await use_case(VerifyEmailInput(token=token))
        except BaseDomainError as exc:
            return Template('account/result.html', context=_result_context(error=exc.detail))
        return Template(
            'account/result.html',
            context=_result_context(message='Your email address is verified. You can sign in now.'),
        )

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
        result = await use_case(
            RequestPasswordResetInput(
                email=data.email,
                ip_address=client_ip(request),
            )
        )
        return {'success': result.success}

    @post(
        '/reset-password',
        status_code=HTTP_200_OK,
        summary='Reset password',
        description=(
            'The token identifies the user. No authentication and no user id are required — '
            'supplying one from an unauthenticated request checked nothing and made the '
            'endpoint impossible to reach from an email link.'
        ),
        tags=['auth'],
    )
    @inject
    async def reset_password(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: ResetPasswordSchema,
        use_case: FromDishka[ResetPasswordUseCase],
    ) -> dict[str, bool]:
        result = await use_case(
            ResetPasswordInput(
                token=data.token,
                new_password=data.new_password,
                ip_address=client_ip(request),
            )
        )
        return {'success': result.success}

    @get(
        '/reset-password',
        status_code=HTTP_200_OK,
        summary='Password reset form (link from the email)',
        description='The form the password-reset email links to.',
        tags=['auth'],
        include_in_schema=False,
    )
    async def reset_password_form(self, token: FromQuery[str]) -> Template:
        return Template('account/reset_password.html', context={'token': token})

    @post(
        '/2fa/enable',
        status_code=HTTP_200_OK,
        summary='Enable two-factor authentication',
        tags=['2fa'],
        guards=[require_scope(SCOPE_ACCOUNT_WRITE)],
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
        '/2fa/confirm',
        status_code=HTTP_200_OK,
        summary='Confirm a pending two-factor enrolment',
        description='Activates 2FA once the user proves the authenticator holds the secret.',
        tags=['2fa'],
        guards=[require_scope(SCOPE_ACCOUNT_WRITE)],
    )
    @inject
    async def confirm_2fa(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: TwoFactorVerifyRequestSchema,
        use_case: FromDishka[Confirm2FAUseCase],
    ) -> dict[str, bool]:
        await use_case(request.user.user_id, Confirm2FAInput(code=data.code))
        return {'success': True}

    @post(
        '/2fa/disable',
        status_code=HTTP_200_OK,
        summary='Disable two-factor authentication',
        tags=['2fa'],
        guards=[require_scope(SCOPE_ACCOUNT_WRITE)],
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
        guards=[require_scope(SCOPE_PROFILE)],
    )
    @inject
    async def get_sessions(
        self,
        request: Request[UserSecuritySchema, Token, State],
        use_case: FromDishka[GetUserSessionsUseCase],
        # Typed and bounded by Litestar: `int(query_params.get('limit'))` turned `?limit=abc`
        # into a 500 and accepted an unbounded page size.
        limit: Annotated[int, Parameter(ge=1, le=100)] = 20,
        offset: Annotated[int, Parameter(ge=0)] = 0,
    ) -> SessionsPageResponseSchema:
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
        guards=[require_scope(SCOPE_SESSIONS_WRITE)],
    )
    @inject
    async def revoke_session(
        self,
        request: Request[UserSecuritySchema, Token, State],
        session_id: FromPath[str],
        use_case: FromDishka[RevokeSessionUseCase],
    ) -> None:
        await use_case(request.user.user_id, session_id)

    @delete(
        '/',
        status_code=HTTP_200_OK,
        summary='Revoke all sessions',
        tags=['sessions'],
        guards=[require_scope(SCOPE_SESSIONS_WRITE)],
    )
    @inject
    async def revoke_all_sessions(
        self,
        request: Request[UserSecuritySchema, Token, State],
        use_case: FromDishka[RevokeAllSessionsUseCase],
    ) -> None:
        await use_case(request.user.user_id)
