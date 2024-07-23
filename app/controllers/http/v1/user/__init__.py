from fastapi import APIRouter

from . import (
    create,
    retreive,
)

router = APIRouter(prefix='/user', tags=['user'])
router.include_router(create.router)
router.include_router(retreive.router)
