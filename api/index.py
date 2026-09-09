from fastapi import Request

from api.app import app
from api.ui import ui as render_ui


@app.middleware("http")
async def normalize_vercel_function_path(request: Request, call_next):
    path = request.scope.get("path", "")
    prefix = "/api/index.py"
    if path == prefix or path.startswith(prefix + "/"):
        request.scope["path"] = path[len(prefix):] or "/"
        request.scope["raw_path"] = request.scope["path"].encode("utf-8")
    return await call_next(request)


@app.get("/", include_in_schema=False)
def root_ui():
    return render_ui()


__all__ = ["app"]
