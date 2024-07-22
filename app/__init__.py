from .main import get_fastapi_app
from .main import get_faststream_app

fastapi = get_fastapi_app()
faststream = get_faststream_app()

__all__ = ["fastapi", "faststream"]
