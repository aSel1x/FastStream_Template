from .app import App

app = App()
fastapi = app.get_http_worker()
faststream = app.get_amqp_worker()

__all__ = ["fastapi", "faststream"]
