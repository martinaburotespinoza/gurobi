from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gurobean.assistant import ask


def main() -> int:
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print("Uso: python scripts\\ask_gurobean_ai.py \"tu pregunta\"")
        return 2
    result = ask(question)
    print(result["answer"])
    print(f"\nprovider={result['provider']} grounded={result['grounded']}")
    if result.get("model"):
        print(f"model={result['model']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
