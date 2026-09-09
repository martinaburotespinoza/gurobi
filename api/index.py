from api.app import app
from api.public_router import router

app.include_router(router)

__all__ = ["app"]
