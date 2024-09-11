from .main import setup_faststream
from .main import setup_fastapi
from .main import setup_taskiq

faststream_app = setup_faststream()
fastapi_app = setup_fastapi()
taskiq_app = setup_taskiq()

amqp = faststream_app.app
backend = fastapi_app.app
scheduler = taskiq_app.scheduler
