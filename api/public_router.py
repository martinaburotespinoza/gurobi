from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()
ROOT = Path(__file__).resolve().parent.parent


def _manifest() -> dict:
    path = ROOT / "certification_manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "UNAVAILABLE", "gates": {}}


def _gurobi() -> dict:
    available = importlib.util.find_spec("gurobipy") is not None
    if not available:
        return {"available": False, "version": None, "licensed": False}
    try:
        import gurobipy as gp
        version = ".".join(str(x) for x in gp.gurobi.version())
        try:
            env = gp.Env(empty=True)
            env.setParam("OutputFlag", 0)
            env.start()
            env.dispose()
            licensed = True
        except Exception:
            licensed = False
        return {"available": True, "version": version, "licensed": licensed}
    except Exception as exc:
        return {"available": True, "version": None, "licensed": False, "error": type(exc).__name__}


@router.get("/status")
@router.get("/api/status")
def status() -> dict:
    manifest = _manifest()
    gates = manifest.get("gates", {})
    gb = _gurobi()
    return {
        "ok": True,
        "service": "gurobean-engine",
        "gurobi": gb,
        "certification": {
            "manifest_status": manifest.get("status", "UNKNOWN"),
            "r1_r4_reference": gates.get("r1_r4_reference"),
            "r8_core_math_validation": gates.get("r8_core_math_validation"),
            "r9_release": gates.get("r9_release"),
            "real_game_evidence": all(gates.get(k) == "PASS" for k in ("r5_markup_published_relationship", "r6_balking", "r7_multi_cup", "r8_service_rate")),
        },
        "truth_policy": {
            "missing_gurobi_is_pass": False,
            "synthetic_evidence_can_promote": False,
            "release_requires_post_patch_validation": True,
        },
    }


@router.get("/capture")
@router.get("/app/capture")
def capture() -> FileResponse:
    path = ROOT / "web" / "capture.html"
    if not path.is_file():
        raise HTTPException(status_code=500, detail="web/capture.html not found")
    return FileResponse(path, media_type="text/html")


@router.get("/app")
def app_alias() -> FileResponse:
    path = ROOT / "web" / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=500, detail="web/index.html not found")
    return FileResponse(path, media_type="text/html")
