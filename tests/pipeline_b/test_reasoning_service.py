from datetime import datetime, timezone
from types import SimpleNamespace

from pipeline_b.cache import response_cache
from pipeline_b.engines import generator
from pipeline_b.schemas.input import ClinicalField, PatientRecord
from pipeline_b.schemas.query import ClassifiedQuery, PersonaType, QueryType
from pipeline_b.services import patient_service, reasoning_service


def _field(index: int, is_abnormal: bool | None = None) -> ClinicalField:
    return ClinicalField(
        field_id=f"job-1_field-{index}",
        job_id="job-1",
        patient_id="patient-1",
        document_type="lab_report",
        collection_date="2025-01-01",
        processed_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
        name=f"field-{index}",
        raw_name=f"field-{index}",
        value=str(index),
        numeric_value=float(index),
        unit="u",
        reference_range="1 - 10",
        ref_low=1.0,
        ref_high=10.0,
        is_abnormal=is_abnormal,
    )


def _record(fields: list[ClinicalField]) -> PatientRecord:
    return PatientRecord(
        patient_id="patient-1",
        job_id="job-1",
        document_type="lab_report",
        processed_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
        structured_text="",
        fields=fields,
    )


def _query(text="explain"):
    return ClassifiedQuery(
        text=text,
        persona=PersonaType.doctor,
        query_type=QueryType.reasoning,
        confidence=1.0,
        classification_method="rule",
        patient_id="patient-1",
    )


class FakeChain:
    def __init__(self, result):
        self.result = result

    def __or__(self, other):
        return self

    def invoke(self, payload):
        return self.result


class FakeLLM:
    def bind(self, **kwargs):
        return self


def test_doctor_prompt_used_for_doctor(monkeypatch):
    captured = {}
    result = {
        "interpretation": "ok",
        "clinical_significance": "none",
        "possible_conditions": [],
        "critical_flags": [],
        "confidence": 0.9,
        "citations": [],
    }

    def fake_from_messages(messages):
        captured["messages"] = messages
        return FakeChain(result)

    monkeypatch.setattr(generator.ChatPromptTemplate, "from_messages", fake_from_messages)
    monkeypatch.setattr(generator, "_get_llm", lambda: FakeLLM())

    output = generator.generate_doctor_reasoning([_field(1)], "question")

    assert output["interpretation"] == "ok"
    assert captured["messages"][0].content == generator.DOCTOR_SYSTEM


def test_patient_prompt_used_for_patient(monkeypatch):
    captured = {}
    result = {"response": "simple", "simplified_fields": []}

    def fake_from_messages(messages):
        captured["messages"] = messages
        return FakeChain(result)

    monkeypatch.setattr(generator.ChatPromptTemplate, "from_messages", fake_from_messages)
    monkeypatch.setattr(generator, "_get_llm", lambda: FakeLLM())

    output = generator.generate_patient_explanation([_field(1)], "question")

    assert output["response"] == "simple"
    assert captured["messages"][0].content == generator.PATIENT_SYSTEM


def test_disclaimer_always_present(monkeypatch):
    query = ClassifiedQuery(
        text="what does this mean",
        persona=PersonaType.patient,
        query_type=QueryType.patient_chat,
        confidence=1.0,
        classification_method="rule",
        patient_id="patient-1",
    )
    monkeypatch.setattr(
        patient_service,
        "get_all_records_for_patient",
        lambda patient_id, db: [_record([_field(1, False)])],
    )
    monkeypatch.setattr(
        patient_service,
        "generate_patient_explanation",
        lambda fields, text: {"response": "ok", "simplified_fields": []},
    )

    result = patient_service.handle_patient_query(query, "patient-1", object())

    assert result.disclaimer
    assert result.disclaimer == patient_service.DISCLAIMER


def test_safety_blocked_on_diagnosis_query(monkeypatch):
    query = ClassifiedQuery(
        text="can you diagnose me",
        persona=PersonaType.patient,
        query_type=QueryType.patient_chat,
        confidence=1.0,
        classification_method="rule",
        patient_id="patient-1",
    )
    called = {"llm": False}

    def fail_if_called(fields, text):
        called["llm"] = True
        raise AssertionError("LLM should not be called")

    monkeypatch.setattr(patient_service, "generate_patient_explanation", fail_if_called)

    result = patient_service.handle_patient_query(query, "patient-1", object())

    assert result.safety_blocked is True
    assert called["llm"] is False


def test_context_capped_at_15_fields():
    fields = [_field(i, is_abnormal=(i % 2 == 0)) for i in range(20)]

    context = generator._build_context(fields)

    assert len(context.splitlines()) == 15


def test_cached_result_returned(monkeypatch):
    query = _query()
    key = response_cache.make_cache_key(f"{query.text}|filters={{}}", "patient-1", "reasoning")
    response_cache.set_cache(
        key,
        {
            "interpretation": "cached",
            "clinical_significance": "cached",
            "possible_conditions": [],
            "critical_flags": [],
            "confidence": 1.0,
            "citations": [],
            "data_used": [],
        },
        "reasoning",
    )
    monkeypatch.setattr(
        reasoning_service,
        "generate_doctor_reasoning",
        lambda fields, text: (_ for _ in ()).throw(AssertionError("LLM called")),
    )
    monkeypatch.setattr(
        reasoning_service,
        "get_all_records_for_patient",
        lambda patient_id, db: (_ for _ in ()).throw(AssertionError("DB called")),
    )

    result = reasoning_service.handle_reasoning_query(query, "patient-1", object())

    assert result.interpretation == "cached"
    assert result.cached is True
