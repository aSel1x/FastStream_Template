from typing import Annotated, final
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.litestar import inject
from litestar import Controller, get, post
from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException
from litestar.params import Body, FromQuery
from litestar.response import Redirect, Template
from litestar.status_codes import HTTP_400_BAD_REQUEST
from pydantic import BaseModel

from application.common.exceptions import TooManyLoginAttemptsError
from application.common.interfaces.system.rate_limiter import RateLimiterInterface
from application.user.commands.complete_two_factor import (
    CompleteTwoFactorInput,
    CompleteTwoFactorUseCase,
)
from application.user.commands.login import LoginInput, LoginUseCase
from application.user.queries.id_token_claims import (
    BuildConsentClaimsUseCase,
    ConsentClaimsInput,
)
from application.user.two_factor_challenge import TwoFactorChallengeExpiredError
from domain.user.exceptions import AccountLockedError, InvalidCredentialsError
from infrastructure.hydra import (
    HydraAdminClient,
    HydraChallengeNotFoundError,
    HydraConfig,
    HydraConsentRequest,
    HydraRedirect,
)
from presentation.http.client_ip import client_ip_or_unknown

#: ACR value published to relying parties when the login included a second factor.
ACR_TWO_FACTOR = 'urn:acr:2fa'


class LoginFormData(BaseModel):
    login_challenge: str
    username: str | None = None
    password: str | None = None
    two_factor_code: str | None = None
    pending_token: str | None = None


class ConsentFormData(BaseModel):
    consent_challenge: str
    approve: str = 'false'


def _login_template(
    login_challenge: str,
    *,
    error: str = '',
    requires_two_factor: bool = False,
    pending_token: str = '',
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
        login_challenge: FromQuery[str],
    ) -> Template | Redirect:
        try:
            login_request = await hydra.get_login_request(login_challenge)
        except HydraChallengeNotFoundError as e:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail='Unknown or expired login request'
            ) from e

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
        complete_2fa: FromDishka[CompleteTwoFactorUseCase],
        rate_limiter: FromDishka[RateLimiterInterface],
        config: FromDishka[HydraConfig],
    ) -> Template | Redirect:
        client_host = client_ip_or_unknown(request)

        if data.pending_token:
            return await self._submit_two_factor(
                data,
                hydra,
                complete_2fa,
                rate_limiter,
                config,
                client_host,
            )

        if not data.username or not data.password:
            return _login_template(data.login_challenge, error='Username and password are required')

        try:
            result = await login_use_case(
                LoginInput(
                    username=data.username,
                    password=data.password,
                    ip_address=client_host,
                    user_agent=request.headers.get('user-agent'),
                    login_challenge=data.login_challenge,
                )
            )
        except (InvalidCredentialsError, AccountLockedError, TooManyLoginAttemptsError) as e:
            return _login_template(data.login_challenge, error=e.detail)

        if result.requires_two_factor:
            # The login use case already stashed the challenge; the form just carries its token.
            return _login_template(
                data.login_challenge,
                requires_two_factor=True,
                pending_token=result.challenge_token or '',
            )

        redirect = await hydra.accept_login_request(
            data.login_challenge,
            subject=str(result.user_id),
            remember=True,
            remember_for=config.login_remember_seconds,
            amr=['pwd'],
            context={'user_id': str(result.user_id), 'session_id': result.session_id},
        )
        return Redirect(redirect.redirect_to)

    async def _submit_two_factor(
        self,
        data: LoginFormData,
        hydra: HydraAdminClient,
        complete_2fa: CompleteTwoFactorUseCase,
        rate_limiter: RateLimiterInterface,
        config: HydraConfig,
        client_host: str,
    ) -> Template | Redirect:
        """The second half of a browser login.

        Runs through the same challenge use case as the JSON API, so the two entry points
        cannot disagree on whether the second factor is actually required.
        """
        pending_token = data.pending_token or ''

        limit = await rate_limiter.check(f'2fa:{client_host}')
        if not limit.allowed:
            return _login_template(
                data.login_challenge,
                error='Too many attempts, try again later',
                requires_two_factor=True,
                pending_token=pending_token,
            )

        if not data.two_factor_code:
            return _login_template(
                data.login_challenge,
                error='Two-factor code is required',
                requires_two_factor=True,
                pending_token=pending_token,
            )

        try:
            result = await complete_2fa(
                CompleteTwoFactorInput(
                    challenge_token=pending_token,
                    code=data.two_factor_code,
                )
            )
        except TwoFactorChallengeExpiredError:
            return _login_template(
                data.login_challenge,
                error='Invalid code, or the challenge expired. Please sign in again.',
            )

        redirect = await hydra.accept_login_request(
            result.login_challenge or data.login_challenge,
            subject=str(result.user_id),
            remember=True,
            remember_for=config.login_remember_seconds,
            # Tells the relying party that a second factor was actually presented.
            acr=ACR_TWO_FACTOR,
            amr=['pwd', 'otp'],
            context={'user_id': str(result.user_id), 'session_id': result.session_id},
        )
        return Redirect(redirect.redirect_to)

    @get('/consent')
    @inject
    async def consent_form(
        self,
        hydra: FromDishka[HydraAdminClient],
        build_claims: FromDishka[BuildConsentClaimsUseCase],
        config: FromDishka[HydraConfig],
        consent_challenge: FromQuery[str],
    ) -> Template | Redirect:
        try:
            consent_request = await hydra.get_consent_request(consent_challenge)
        except HydraChallengeNotFoundError as e:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail='Unknown or expired consent request'
            ) from e

        if consent_request.skip:
            redirect = await self._accept_consent(hydra, build_claims, config, consent_request)
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
        build_claims: FromDishka[BuildConsentClaimsUseCase],
        config: FromDishka[HydraConfig],
    ) -> Redirect:
        if data.approve != 'true':
            redirect = await hydra.reject_consent_request(
                data.consent_challenge,
                error='access_denied',
                error_description='User denied consent',
            )
            return Redirect(redirect.redirect_to)

        try:
            consent_request = await hydra.get_consent_request(data.consent_challenge)
        except HydraChallengeNotFoundError as e:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail='Unknown or expired consent request'
            ) from e

        redirect = await self._accept_consent(hydra, build_claims, config, consent_request)
        return Redirect(redirect.redirect_to)

    async def _accept_consent(
        self,
        hydra: HydraAdminClient,
        build_claims: BuildConsentClaimsUseCase,
        config: HydraConfig,
        consent_request: HydraConsentRequest,
    ) -> HydraRedirect:
        raw_user_id = consent_request.context.get('user_id')
        session_id = consent_request.context.get('session_id')
        grant_scope = consent_request.requested_scope

        user_id: UUID | None = None
        if isinstance(raw_user_id, str):
            try:
                user_id = UUID(raw_user_id)
            except ValueError as e:
                raise HTTPException(
                    status_code=HTTP_400_BAD_REQUEST, detail='Invalid consent context'
                ) from e

        claims = await build_claims(
            ConsentClaimsInput(
                user_id=user_id,
                session_id=session_id if isinstance(session_id, str) else None,
                granted_scopes=grant_scope,
            )
        )
        id_token_claims = claims.id_token
        access_token_claims = claims.access_token

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
        logout_challenge: FromQuery[str],
    ) -> Redirect:
        try:
            _ = await hydra.get_logout_request(logout_challenge)
            redirect = await hydra.accept_logout_request(logout_challenge)
        except HydraChallengeNotFoundError as e:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST, detail='Unknown or expired logout request'
            ) from e
        return Redirect(redirect.redirect_to)
