from pipeline_b.engines import query_classifier
from pipeline_b.schemas.query import PersonaType, QueryType


def test_rule_match_trend_query():
    result = query_classifier.classify("show trend over time", PersonaType.doctor)

    assert result.query_type == QueryType.trend
    assert result.classification_method == "rule"


def test_rule_match_retrieval_query():
    result = query_classifier.classify("show me find patients", PersonaType.doctor)

    assert result.query_type == QueryType.retrieval
    assert result.classification_method == "rule"


def test_rule_match_requires_two_keywords(monkeypatch):
    monkeypatch.setattr(query_classifier, "embed_single", lambda query: [0.0])
    monkeypatch.setattr(
        query_classifier,
        "_embedding_classify",
        lambda query_vec: (QueryType.reasoning, 0.8),
    )

    result = query_classifier.classify("trend", PersonaType.doctor)

    assert result.classification_method == "embedding"
    assert result.query_type == QueryType.reasoning


def test_patient_persona_never_routes_doctor():
    result = query_classifier.classify("what is my blood result", PersonaType.patient)

    assert result.persona == PersonaType.patient


def test_classification_method_logged():
    result = query_classifier.classify("show me find patients", PersonaType.doctor)

    assert result.classification_method in ["rule", "embedding", "llm"]
