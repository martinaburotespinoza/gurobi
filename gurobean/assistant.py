from __future__ import annotations

"""Free, evidence-grounded assistant for Gurobean.

The assistant is deliberately downstream of the optimization engine: it can read
known project evidence and explain results, but it never changes model inputs,
solver settings, certification gates, or optimization results.

If Ollama is available locally, a free local LLM can turn the evidence context
into natural-language answers. Without Ollama, deterministic answers remain
available for the most important evaluation questions.
"""

import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "llama3.2:3b"


def _load_json(name: str) -> Any:
    path = ROOT / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def evidence_context() -> dict[str, Any]:
    """Return only project evidence safe for LLM grounding."""
    manifest = _load_json("certification_manifest.json")
    validation = _load_json("validation_report.json")
    parity = _load_json("parity_report.json")
    return {
        "project": "Gurobean Engine v2_6",
        "purpose": "Optimization of coffee production decisions under uncertain demand and limited resources.",
        "evaluation": {
            "notebook": "Model mathematical evolution Round by Round.",
            "product": "Dynamic program configurable at runtime without rewriting code.",
            "presentation": "Explain decision variables, objective, constraints and Monte Carlo conceptually; demo live; validate against real values after prediction.",
        },
        "rounds": {
            "R1": "hot coffee — analytical/Gurobi certified",
            "R2": "hot + cold coffee and shared resources — analytical/Gurobi certified",
            "R3": "brewing cost — analytical/Gurobi certified",
            "R4": "hot + cold + costs + resources — analytical/Gurobi certified",
            "R5": "markup / arrival response — operational Monte Carlo; formal game parity evidence-gated",
            "R6": "balking / congestion — operational Monte Carlo; formal game parity evidence-gated",
            "R7": "multi-cup order size — operational Monte Carlo; formal game parity evidence-gated",
            "R8": "service rate / barista cost — operational Monte Carlo; formal game parity evidence-gated",
        },
        "certification_manifest": manifest,
        "validation_report": validation,
        "parity_report": parity,
    }


def _facts_text(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, indent=2, default=str)[:18000]


def _deterministic_answer(question: str, context: dict[str, Any]) -> str:
    q = question.lower().strip()
    if any(k in q for k in ("r1", "round 1", "primera ronda")):
        return "R1 resuelve la decisión de cuánto café caliente preparar. El objetivo es maximizar el beneficio esperado considerando demanda incierta y recursos disponibles."
    if any(k in q for k in ("r2", "round 2", "segunda ronda")):
        return "R2 agrega café frío y acopla las decisiones mediante recursos compartidos. La estructura base se conserva y se incorpora una segunda variable de decisión."
    if any(k in q for k in ("r3", "round 3", "tercera ronda")):
        return "R3 incorpora el costo de preparación. Ese costo modifica directamente el beneficio esperado y, por tanto, la cantidad económicamente conveniente de producir."
    if any(k in q for k in ("r4", "round 4", "cuarta ronda")):
        return "R4 combina café caliente y frío, costos de preparación y restricciones de recursos compartidos. Es la última ronda respaldada por referencia analítica y certificación Gurobi en el estado actual."
    if "r5" in q or "r6" in q or "r7" in q or "r8" in q:
        return "R5–R8 ya son ejecutables mediante simulación Monte Carlo con parámetros de respuesta explícitos. El resultado es operacional, pero la paridad formal contra el juego real sigue protegida por el gate de evidencia: no se declara certificación sin observaciones reales."
    if any(k in q for k in ("gurobi", "solver", "óptim", "optima", "optimal")):
        return "La ruta Gurobi de R1–R4 usa el backend PWL explícito con GenConstrPWL y una auditoría posterior contra la referencia analítica. R5–R8 usan simulación porque el sistema es estocástico y no lineal; su certificación contra el juego requiere evidencia real."
    if any(k in q for k in ("evaluación", "evaluacion", "gerente", "presentación", "presentacion")):
        return "Para la evaluación, el producto debe poder configurarse en vivo sin reescribir código, aceptar nuevos valores de entrada, resolver con agilidad y mostrar la decisión óptima junto con indicadores. La presentación debe explicar la lógica matemática, no el código."
    return "Puedo responder con la evidencia disponible del sistema. Para preguntas sobre una ejecución concreta, entrega los datos/resultados de esa ejecución o consulta el endpoint de resultados para que la respuesta quede anclada a hechos verificables."


def ask(question: str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Answer a question using evidence first and an optional free local LLM."""
    if not question or not question.strip():
        raise ValueError("question must not be empty")
    ctx = context or evidence_context()
    facts = _facts_text(ctx)
    provider = os.getenv("GUROBEAN_AI_PROVIDER", "auto").lower()
    model = os.getenv("GUROBEAN_AI_MODEL", DEFAULT_MODEL)
    url = os.getenv("GUROBEAN_OLLAMA_URL", DEFAULT_OLLAMA_URL)

    if provider in {"auto", "ollama"}:
        payload = {
            "model": model,
            "prompt": (
                "Eres el asistente de Gurobean. Responde en español. "
                "Usa exclusivamente el contexto entregado. No inventes resultados, "
                "reglas ni cifras. Distingue hechos del sistema de explicaciones. "
                "Si falta evidencia, dilo claramente.\n\n"
                f"CONTEXTO:\n{facts}\n\nPREGUNTA:\n{question.strip()}"
            ),
            "stream": False,
            "options": {"temperature": 0.1},
        }
        try:
            req = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
            answer = str(data.get("response", "")).strip()
            if answer:
                return {"ok": True, "answer": answer, "provider": "ollama", "model": model, "grounded": True}
        except (OSError, URLError, TimeoutError, json.JSONDecodeError):
            if provider == "ollama":
                raise RuntimeError("Ollama no está disponible en la URL configurada")

    return {"ok": True, "answer": _deterministic_answer(question, ctx), "provider": "local-evidence", "model": None, "grounded": True}
