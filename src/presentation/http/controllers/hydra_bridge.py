import secrets
from typing import Annotated, final
from uuid import UUID

from application.common.exceptions import TooManyLoginAttemptsError
from application.common.interfaces.system.cache import CacheInterface
from application.common.interfaces.system.rate_limiter import RateLimiterInterface
from application.user.commands.login import LoginInput, LoginUseCase
from application.user.commands.manage_2fa import Verify2FAInput, Verify2FAUseCase
from domain.user.exceptions import AccountLockedError, InvalidCredentialsError
from domain.user.interfaces.persistence.readers import UserReader
from domain.user.value_objects import UserID
from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, post
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.params import Body
from litestar.response import Redirect, Template
from litestar.status_codes import HTTP_400_BAD_REQUEST
from pydantic import BaseModel, JsonValue, ValidationError

from infrastructure.hydra import (
    HydraAdminClient,
    HydraChallengeNotFoundError,
    HydraConfig,
    HydraConsentRequest,
    HydraRedirect,
)

_PENDING_2FA_TTL_SECONDS = 300


class LoginFormData(BaseModel):
    login_challenge: str
    username: str | None = None
    password: str | None = None
    two_factor_code: str | None = None
    pending_token: str | None = None


class ConsentFormData(BaseModel):
    consent_challenge: str
    approve: str = 'false'


class _Pending2FASession(BaseModel):
    user_id: str
    session_id: str
    login_challenge: str


def _login_template(
    login_challenge: str, *, error: str = '', requires_two_factor: bool = False, pending_token: str = '',
) -> Template:
    return Template(
        'login.html',
        context={
            'login_challenge': login_challenge,
            'error': error,
            'requires_two_factor': requires_two_factor,
            'pending_token': pending_token,
        },
    )


@final
class HydraBridgeController(Controller):
    path = '/auth'

    @get('/login')
    @inject
    async def login_form(
        self,
        hydra: FromDishka[HydraAdminClient],
        login_challenge: str,
    ) -> Template | Redirect:
        try:
            login_request = await hydra.get_login_request(login_challenge)
        except HydraChallengeNotFoundError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='Unknown or expired login request') from e

        if login_request.skip and login_request.subject:
            result = await hydra.accept_login_request(
                login_challenge,
                subject=login_request.subject,
                context={'user_id': login_request.subject},
            )
            return Redirect(result.redirect_to)

        return _login_template(login_challenge)

    @post('/login')
    @inject
    async def login_submit(
        self,
        request: ASGIConnection[object, object, object, State],
        data: Annotated[LoginFormData, Body(media_type=RequestEncodingType.URL_ENCODED)],
        hydra: FromDishka[HydraAdminClient],
        login_use_case: FromDishka[LoginUseCase],
        verify_2fa_use_case: FromDishka[Verify2FAUseCase],
        cache: FromDishka[CacheInterface],
        rate_limiter: FromDishka[RateLimiterInterface],
        config: FromDishka[HydraConfig],
    ) -> Template | Redirect:
        client_host = request.client.host if request.client else 'unknown'

        if data.pending_token:
            return await self._submit_two_factor(
                data, hydra, verify_2fa_use_case, cache, rate_limiter, config, client_host,
            )

        if not data.username or not data.password:
            return _login_template(data.login_challenge, error='Username and password are required')

        try:
            result = await login_use_case(LoginInput(
                username=data.username,
                password=data.password,
                ip_address=client_host,
                user_agent=request.headers.get('user-agent'),
            ))
        except (InvalidCredentialsError, AccountLockedError, TooManyLoginAttemptsError) as e:
            return _login_template(data.login_challenge, error=e.detail)

        if result.requires_two_factor:
            pending_token = secrets.token_urlsafe(32)
            await cache.set(
                f'pending_2fa:{pending_token}',
                _Pending2FASession(
                    user_id=str(result.user_id),
                    session_id=result.session_id,
                    login_challenge=data.login_challenge,
                ).model_dump_json(),
                ttl_seconds=_PENDING_2FA_TTL_SECONDS,
            )
            return _login_template(data.login_challenge, requires_two_factor=True, pending_token=pending_token)

        redirect = await hydra.accept_login_request(
            data.login_challenge,
            subject=str(result.user_id),
            remember=True,
            remember_for=config.login_remember_seconds,
            context={'user_id': str(result.user_id), 'session_id': result.session_id},
        )
        return Redirect(redirect.redirect_to)

    async def _submit_two_factor(
        self,
        data: LoginFormData,
        hydra: HydraAdminClient,
        verify_2fa_use_case: Verify2FAUseCase,
        cache: CacheInterface,
        rate_limiter: RateLimiterInterface,
        config: HydraConfig,
        client_host: str,
    ) -> Template | Redirect:
        pending_token = data.pending_token or ''

        allowed, _, _ = await rate_limiter.check(f'2fa:{client_host}')
        if not allowed:
            return _login_template(
                data.login_challenge, error='Too many attempts, try again later',
                requires_two_factor=True, pending_token=pending_token,
            )

        cache_key = f'pending_2fa:{pending_token}'
        cached = await cache.get(cache_key)
        if cached is None:
            return _login_template(data.login_challenge, error='Session expired, please log in again')

        try:
            pending = _Pending2FASession.model_validate_json(cached)
        except ValidationError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='Invalid pending 2FA session') from e

        if not data.two_factor_code:
            return _login_template(
                data.login_challenge, error='Two-factor code is required',
                requires_two_factor=True, pending_token=pending_token,
            )

        try:
            pending_user_id = UUID(pending.user_id)
        except ValueError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='Invalid pending 2FA session') from e

        verify_result = await verify_2fa_use_case(
            pending_user_id, Verify2FAInput(code=data.two_factor_code),
        )
        if not verify_result.success:
            return _login_template(
                data.login_challenge, error='Invalid two-factor code',
                requires_two_factor=True, pending_token=pending_token,
            )

        await cache.delete(cache_key)
        redirect = await hydra.accept_login_request(
            pending.login_challenge,
            subject=pending.user_id,
            remember=True,
            remember_for=config.login_remember_seconds,
            context={'user_id': pending.user_id, 'session_id': pending.session_id},
        )
        return Redirect(redirect.redirect_to)

    @get('/consent')
    @inject
    async def consent_form(
        self,
        hydra: FromDishka[HydraAdminClient],
        user_reader: FromDishka[UserReader],
        config: FromDishka[HydraConfig],
        consent_challenge: str,
    ) -> Template | Redirect:
        try:
            consent_request = await hydra.get_consent_request(consent_challenge)
        except HydraChallengeNotFoundError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='Unknown or expired consent request') from e

        if consent_request.skip:
            redirect = await self._accept_consent(hydra, user_reader, config, consent_request)
            return Redirect(redirect.redirect_to)

        return Template(
            'consent.html',
            context={
                'consent_challenge': consent_challenge,
                'client_name': consent_request.client.client_name,
                'scopes': consent_request.requested_scope,
            },
        )

    @post('/consent')
    @inject
    async def consent_submit(
        self,
        data: Annotated[ConsentFormData, Body(media_type=RequestEncodingType.URL_ENCODED)],
        hydra: FromDishka[HydraAdminClient],
        user_reader: FromDishka[UserReader],
        config: FromDishka[HydraConfig],
    ) -> Redirect:
        if data.approve != 'true':
            redirect = await hydra.reject_consent_request(
                data.consent_challenge, error='access_denied', error_description='User denied consent',
            )
            return Redirect(redirect.redirect_to)

        try:
            consent_request = await hydra.get_consent_request(data.consent_challenge)
        except HydraChallengeNotFoundError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='Unknown or expired consent request') from e

        redirect = await self._accept_consent(hydra, user_reader, config, consent_request)
        return Redirect(redirect.redirect_to)

    async def _accept_consent(
        self,
        hydra: HydraAdminClient,
        user_reader: UserReader,
        config: HydraConfig,
        consent_request: HydraConsentRequest,
    ) -> HydraRedirect:
        user_id = consent_request.context.get('user_id')
        session_id = consent_request.context.get('session_id')
        grant_scope = consent_request.requested_scope

        id_token_claims: dict[str, JsonValue] = {}
        if isinstance(user_id, str):
            try:
                parsed_user_id = UUID(user_id)
            except ValueError as e:
                raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='Invalid consent context') from e
            user = await user_reader.get_by_id(UserID(parsed_user_id))
            if user:
                if 'profile' in grant_scope:
                    id_token_claims['preferred_username'] = user.username
                if 'email' in grant_scope:
                    id_token_claims['email'] = user.email
                    id_token_claims['email_verified'] = user.is_email_verified

        access_token_claims: dict[str, JsonValue] = (
            {'session_id': session_id} if isinstance(session_id, str) else {}
        )

        return await hydra.accept_consent_request(
            consent_request.challenge,
            grant_scope=grant_scope,
            remember=True,
            remember_for=config.consent_remember_seconds,
            id_token_claims=id_token_claims,
            access_token_claims=access_token_claims,
        )

    @get('/logout')
    @inject
    async def logout(
        self,
        hydra: FromDishka[HydraAdminClient],
        logout_challenge: str,
    ) -> Redirect:
        try:
            _ = await hydra.get_logout_request(logout_challenge)
            redirect = await hydra.accept_logout_request(logout_challenge)
        except HydraChallengeNotFoundError as e:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='Unknown or expired logout request') from e
        return Redirect(redirect.redirect_to)
