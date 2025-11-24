from typing import Annotated
from uuid import UUID

from application.user.interactors.create_user import (
    CreateUserInputDTO,
    CreateUserInteractor,
)
from application.user.interactors.delete_me import DeleteMeInteractor
from application.user.interactors.get_me import GetMeInteractor, GetMeOutputDTO
from application.user.interactors.login import (
    LoginInputDTO,
    LoginInteractor,
    LoginOutputDTO,
)
from application.user.interactors.refresh_token import (
    RefreshTokenInputDTO,
    RefreshTokenInteractor,
    RefreshTokenOutputDTO,
)
from application.user.interactors.update_profile import (
    UpdateProfileInputDTO,
    UpdateProfileInteractor,
    UpdateProfileOutputDTO,
)
from litestar import Controller, Request, delete, get, patch, post
from litestar.datastructures.state import State
from litestar.security.jwt import Token
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from spritze import Depends, inject

from presentation.http.schemas.user import UserProfileUpdatedRequestSchema
from presentation.http.security import UserSecuritySchema


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
        interactor: Annotated[CreateUserInteractor, Depends()],
    ) -> UUID:
        """Create a new user account."""
        return await interactor(data)

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
        interactor: Annotated[LoginInteractor, Depends()],
    ) -> LoginOutputDTO:
        """Authenticate user and return tokens."""
        return await interactor(data)

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
        interactor: Annotated[RefreshTokenInteractor, Depends()],
    ) -> RefreshTokenOutputDTO:
        """Refresh access token using refresh token."""
        return await interactor(data)

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
        interactor: Annotated[GetMeInteractor, Depends()],
    ) -> GetMeOutputDTO:
        """Get authenticated user profile."""

        return await interactor(request.user.user_id)

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
        data: UserProfileUpdatedRequestSchema,
        interactor: Annotated[UpdateProfileInteractor, Depends()],
    ) -> UpdateProfileOutputDTO:
        """Update authenticated user profile."""
        return await interactor(
            UpdateProfileInputDTO(
                user_id=request.user.user_id,
                username=data.username,
                email=data.email,
            )
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
        interactor: Annotated[DeleteMeInteractor, Depends()],
    ) -> None:
        """Delete authenticated user account."""
        return await interactor(request.user.user_id)
