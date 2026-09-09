from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse

from api.app import app
from api.ui import ui as render_ui


ROOT = Path(__file__).resolve().parents[1]
R2_COCKPIT = ROOT / "web" / "r2-cockpit.html"


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


@app.get("/r2-cockpit", include_in_schema=False)
@app.get("/r2-cockpit.html", include_in_schema=False)
def r2_cockpit():
    return FileResponse(R2_COCKPIT, media_type="text/html; charset=utf-8")


__all__ = ["app"]
