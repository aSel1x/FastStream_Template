from typing import Annotated

from application.user.iteractors.create_user import (
    CreateUserInputDTO,
    CreateUserInteractor,
)
from application.user.iteractors.delete_me import DeleteMeInteractor
from application.user.iteractors.get_me import GetMeInteractor, GetMeOutputDTO
from application.user.iteractors.login import LoginInputDTO, LoginInteractor
from application.user.iteractors.refresh_token import (
    RefreshTokenInputDTO,
    RefreshTokenInteractor,
    RefreshTokenOutputDTO,
)
from application.user.iteractors.update_profile import (
    UpdateProfileInputDTO,
    UpdateProfileInteractor,
    UpdateProfileOutputDTO,
)
from litestar import Controller, Request, delete, get, patch, post
from litestar.datastructures.state import State
from litestar.security.jwt import Token
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from spritze import Depends, inject

from presentation.api.security import UserSecuritySchema


class UserController(Controller):
    path: str = '/users'

    @post(
        '/register',
        status_code=HTTP_201_CREATED,
        summary='Register new user',
        tags=['auth'],
    )
    @inject
    async def register(
        self,
        data: CreateUserInputDTO,
        create_user_interactor: Annotated[CreateUserInteractor, Depends()],
    ) -> dict[str, str]:
        """Create a new user account."""
        user_id = await create_user_interactor(data)
        return {'user_id': str(user_id)}

    @post(
        '/login',
        status_code=HTTP_200_OK,
        summary='Authenticate user',
        tags=['auth'],
    )
    @inject
    async def login(
        self,
        data: LoginInputDTO,
        login_interactor: Annotated[LoginInteractor, Depends()],
    ) -> dict[str, str | int]:
        """Authenticate user and return tokens."""
        result = await login_interactor(data)
        return {
            'user_id': result.user_id,
            'access_token': result.access_token,
            'token_type': result.token_type,
            'expires_in': result.expires_in,
            'refresh_token': result.refresh_token,
        }

    @post(
        '/refresh',
        status_code=HTTP_200_OK,
        summary='Refresh access token',
        tags=['auth'],
    )
    @inject
    async def refresh_token(
        self,
        data: RefreshTokenInputDTO,
        refresh_token_interactor: Annotated[RefreshTokenInteractor, Depends()],
    ) -> RefreshTokenOutputDTO:
        """Refresh access token using refresh token."""
        return await refresh_token_interactor(data)

    @get(
        '/me',
        status_code=HTTP_200_OK,
        summary='Get current user profile',
        tags=['users'],
    )
    @inject
    async def get_me(
        self,
        request: Request[UserSecuritySchema, Token, State],
        get_me_interactor: Annotated[GetMeInteractor, Depends()],
    ) -> GetMeOutputDTO:
        """Get authenticated user profile."""

        return await get_me_interactor(request.user.user_id)

    @patch(
        '/me',
        status_code=HTTP_200_OK,
        summary='Update current user profile',
        tags=['users'],
    )
    @inject
    async def update_profile(
        self,
        request: Request[UserSecuritySchema, Token, State],
        data: UpdateProfileInputDTO,
        update_profile_interactor: Annotated[UpdateProfileInteractor, Depends()],
    ) -> UpdateProfileOutputDTO:
        """Update authenticated user profile."""
        return await update_profile_interactor((request.user.user_id, data))

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
        delete_me_interactor: Annotated[DeleteMeInteractor, Depends()],
    ) -> None:
        """Delete authenticated user account."""
        await delete_me_interactor(request.user.user_id)
