from .main import get_amqp_worker
from .main import get_http_worker

fastapi = get_http_worker()
faststream = get_amqp_worker()

__all__ = ["fastapi", "faststream"]
