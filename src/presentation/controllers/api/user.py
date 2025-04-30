from typing import Annotated
from uuid import UUID

from application.user.iteractors.create import CreateUserInputDTO, CreateUserInteractor
from application.user.iteractors.read import ReadUserInteractor
from dishka.entities.depends_marker import FromDishka as Depends
from dishka.integrations.litestar import inject
from domain.user import entities
from litestar import Controller, HttpMethod, route
from litestar.params import Body


class UserController(Controller):
    path = '/user'

    @route('/', http_method=HttpMethod.POST)
    @inject
    async def create(
        self,
        username: Annotated[str, Body()],
        password: Annotated[str, Body()],
        iteractor: Depends[CreateUserInteractor],
    ) -> UUID:
        dto = CreateUserInputDTO(username=username, password=password)
        uuid = await iteractor(dto)
        return uuid

    @route('/{user_id:uuid}', http_method=HttpMethod.GET)
    @inject
    async def read(
        self, user_id: UUID, iteractor: Depends[ReadUserInteractor]
    ) -> entities.User:
        user = await iteractor(user_id)
        return user
