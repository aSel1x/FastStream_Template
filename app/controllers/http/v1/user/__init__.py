from pathlib import Path

from fastapi import APIRouter

from . import (
    create,
    retreive,
)

FOLDER_NAME = Path(__file__).parent.name

router = APIRouter(prefix='/' + FOLDER_NAME, tags=[FOLDER_NAME])
router.include_router(create.router)
router.include_router(retreive.router)
