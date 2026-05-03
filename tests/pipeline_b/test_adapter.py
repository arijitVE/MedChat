from datetime import datetime, timezone
from types import SimpleNamespace

from pipeline_b.adapters.pipeline_a_adapter import (
    _build_clinical_field,
    compute_is_abnormal,
    normalize_field_name,
    parse_reference_range,
)


def _row(name="hgb"):
    return SimpleNamespace(
        job_id="job-1",
        name=name,
        value="10.5",
        unit="g/dL",
        reference_range="11.5 - 16.4 gm/dl",
        collection_date="2025-01-01",
        confidence=0.91,
        status="auto",
    )


def _job():
    return SimpleNamespace(
        job_id="job-1",
        patient_id="patient-1",
        document_type="lab_report",
        processed_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )


def test_parse_reference_range_all_formats():
    cases = [
        ("11.5 - 16.4 gm/dl", (11.5, 16.4)),
        ("FEMALE: 11.5 - 16.4", (11.5, 16.4)),
        ("3.00 - 5.50", (3.0, 5.5)),
        ("4000-11,000", (4000.0, 11000.0)),
        ("50-70", (50.0, 70.0)),
        ("Male 42 52%", (42.0, 52.0)),
        ("0 - 1", (0.0, 1.0)),
        ("Not Found", (None, None)),
        (None, (None, None)),
    ]

    for raw, expected in cases:
        assert parse_reference_range(raw) == expected


def test_compute_is_abnormal_all_cases():
    assert compute_is_abnormal(10.5, 11.5, 16.4) is True
    assert compute_is_abnormal(13.5, 11.5, 16.4) is False
    assert compute_is_abnormal(17.0, 11.5, 16.4) is True
    assert compute_is_abnormal(None, 11.5, 16.4) is None
    assert compute_is_abnormal(13.5, None, None) is None


def test_build_clinical_field_from_db_row():
    field = _build_clinical_field(_row(), _job())

    assert field.field_id == "job-1_hemoglobin"
    assert field.job_id == "job-1"
    assert field.patient_id == "patient-1"
    assert field.document_type == "lab_report"
    assert field.name == "hemoglobin"
    assert field.raw_name == "hgb"
    assert field.numeric_value == 10.5
    assert field.ref_low == 11.5
    assert field.ref_high == 16.4
    assert field.is_abnormal is True


def test_source_type_always_patient():
    field = _build_clinical_field(_row(), _job())
    assert field.source_type == "patient"


def test_canonical_name_normalization():
    assert normalize_field_name("hgb") == "hemoglobin"
    assert _build_clinical_field(_row(name="hgb"), _job()).name == "hemoglobin"
