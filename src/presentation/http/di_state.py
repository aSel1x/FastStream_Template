from dishka import AsyncContainer
from litestar.datastructures.state import State


class DishkaState(State):
    # Declares the type of the `dishka_container` attribute that `setup_dishka` sets on
    # `State` at runtime, so `ASGIConnection[..., DishkaState].state.dishka_container` is typed.
    dishka_container: AsyncContainer
