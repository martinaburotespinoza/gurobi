# Gurobean AI Assistant

Gurobean now includes a downstream knowledge assistant. It is designed for the demo and evaluation without becoming part of the mathematical solver.

## Guarantees

- Reads project evidence from the repository's certification and validation artifacts.
- Does not modify scenarios, solver parameters, certification gates, or optimization results.
- Refuses to invent unsupported R5–R8 rules or numerical evidence.
- Returns `grounded=true` so the UI/API can distinguish evidence-grounded answers.

## Free local LLM

The preferred optional provider is Ollama running locally. No cloud API key is required.

Set:

```powershell
$env:GUROBEAN_AI_PROVIDER="ollama"
$env:GUROBEAN_AI_MODEL="llama3.2:3b"
```

If Ollama is unavailable and provider is `auto` (the default), the assistant falls back to deterministic evidence-grounded answers.

## CLI

```powershell
python scripts\ask_gurobean_ai.py "¿Qué debe mostrar la demo ante el Gerente?"
```

## API

Start the API:

```powershell
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Then use `POST /ai/ask` with:

```json
{"question":"¿Qué cambia en R4?"}
```

The browser console includes the same assistant and points to the local API by default.

## Evaluation boundary

The assistant is an explanatory layer. The certification chain remains:

`inputs → mathematical model → Gurobi/reference solver → feasibility → objective audit → certification evidence`

AI explanations never replace those checks.
