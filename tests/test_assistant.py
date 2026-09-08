from gurobean.assistant import ask, evidence_context


def test_assistant_answers_without_external_provider():
    result = ask("¿Qué debe mostrar la demo ante el Gerente?")
    assert result["ok"] is True
    assert result["grounded"] is True
    assert "decisión óptima" in result["answer"].lower()


def test_assistant_context_contains_round_and_evaluation_evidence():
    context = evidence_context()
    assert context["project"] == "Gurobean Engine v2_6"
    assert "R1" in context["rounds"]
    assert "R8" in context["rounds"]
    assert "presentation" in context["evaluation"]
