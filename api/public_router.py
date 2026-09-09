from __future__ import annotations

import importlib.util
import json
import subprocess
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


def _git_head() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=2
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _r9_artifact() -> dict:
    path = ROOT / "r9_release_certification.json"
    if not path.is_file():
        return {"present": False, "status": "MISSING"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"present": True, "status": "INVALID"}
    return {
        "present": True,
        "status": data.get("status", "UNKNOWN"),
        "git_commit": data.get("git_commit"),
        "gurobi_gate": data.get("gurobi_gate"),
        "cases_checked": data.get("cases_checked"),
        "failures": data.get("failures"),
    }


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


def _readiness(manifest: dict, artifact: dict, head: str | None, gb: dict) -> dict:
    release_pass = (
        artifact.get("present") is True
        and artifact.get("status") == "PASS"
        and artifact.get("gurobi_gate") == "CHECKED"
        and artifact.get("cases_checked") == 400
        and artifact.get("failures") == 0
        and head is not None
        and artifact.get("git_commit") == head
    )
    reference_pass = manifest.get("gates", {}).get("r1_r4_reference") == "PASS"
    math_pass = manifest.get("gates", {}).get("r8_core_math_validation") == "PASS"
    evidence_gated = not all(
        manifest.get("gates", {}).get(key) == "PASS"
        for key in ("r5_markup_published_relationship", "r6_balking", "r7_multi_cup", "r8_service_rate")
    )
    approved = bool(release_pass and reference_pass and math_pass)
    return {
        "approved_for_live_game_test": approved,
        "label": "APPROVED_FOR_LIVE_GAME_TEST" if approved else "NOT_READY",
        "r1_r4_reference": reference_pass,
        "r8_core_math": math_pass,
        "licensed_gurobi": bool(gb.get("licensed")),
        "r9_release": release_pass,
        "r5_r8_calibration_gated": evidence_gated,
        "blocking_reasons": [] if approved else [
            reason for reason, failed in (
                ("R1-R4 reference gate", not reference_pass),
                ("R8 mathematical validation", not math_pass),
                ("licensed Gurobi release artifact tied to current HEAD", not release_pass),
            ) if failed
        ],
    }


@router.get("/status")
@router.get("/api/status")
def status() -> dict:
    manifest = _manifest()
    head = _git_head()
    gb = _gurobi()
    artifact = _r9_artifact()
    readiness = _readiness(manifest, artifact, head, gb)
    gates = manifest.get("gates", {})
    return {
        "ok": True,
        "service": "gurobean-engine",
        "git": {"head": head, "release_line": manifest.get("release_line")},
        "gurobi": gb,
        "certification": {
            "manifest_status": manifest.get("status", "UNKNOWN"),
            "r1_r4_reference": gates.get("r1_r4_reference"),
            "r8_core_math_validation": gates.get("r8_core_math_validation"),
            "r9_release": gates.get("r9_release"),
            "r9_artifact": artifact,
            "real_game_evidence": all(gates.get(k) == "PASS" for k in ("r5_markup_published_relationship", "r6_balking", "r7_multi_cup", "r8_service_rate")),
        },
        "readiness": readiness,
        "truth_policy": {
            "missing_gurobi_is_pass": False,
            "synthetic_evidence_can_promote": False,
            "release_requires_post_patch_validation": True,
            "r9_artifact_must_match_current_head": True,
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
