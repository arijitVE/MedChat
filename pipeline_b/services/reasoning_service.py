import json
import time

from sqlalchemy.orm import Session

from pipeline_b.adapters.pipeline_a_adapter import get_all_records_for_patient
from pipeline_b.cache.response_cache import get_cached, make_cache_key, set_cache
from pipeline_b.engines.generator import generate_doctor_reasoning
from pipeline_b.schemas.input import ClinicalField, PatientRecord
from pipeline_b.schemas.output import ReasoningResult
from pipeline_b.schemas.query import ClassifiedQuery
from shared.logger import get_logger


logger = get_logger(__name__)


def _filter_records(records: list[PatientRecord], filters: dict | None) -> list[PatientRecord]:
    if not filters:
        return records

    scoped_records = records
    job_ids = filters.get("job_ids")
    if isinstance(job_ids, list):
        job_id_set = {str(job_id) for job_id in job_ids}
        scoped_records = [record for record in scoped_records if record.job_id in job_id_set]

    report_limit = filters.get("report_limit")
    if isinstance(report_limit, int) and report_limit > 0:
        scoped_records = sorted(scoped_records, key=lambda record: record.processed_at, reverse=True)[:report_limit]

    return scoped_records


def _filter_fields(fields: list[ClinicalField], filters: dict | None) -> list[ClinicalField]:
    if not filters:
        return fields

    scoped_fields = fields
    if filters.get("abnormal_only") is True:
        scoped_fields = [field for field in scoped_fields if field.is_abnormal is True]

    return scoped_fields


def _max_fields(filters: dict | None) -> int:
    if not filters:
        return 15

    value = filters.get("max_fields")
    if isinstance(value, int):
        return max(1, min(value, 120))
    return 15


def handle_reasoning_query(
    query: ClassifiedQuery,
    patient_id: str,
    db: Session,
) -> ReasoningResult:
    cache_text = f"{query.text}|filters={json.dumps(query.filters or {}, sort_keys=True)}"
    cache_key = make_cache_key(cache_text, patient_id, "reasoning")
    cached = get_cached(cache_key)
    if cached:
        return ReasoningResult.model_validate({**cached, "cached": True})

    records = _filter_records(get_all_records_for_patient(patient_id, db), query.filters)
    all_fields = _filter_fields([f for r in records for f in r.fields], query.filters)
    max_fields = _max_fields(query.filters)

    t_start = time.time()
    raw = generate_doctor_reasoning(all_fields, query.text, max_fields=max_fields)
    llm_latency_ms = round((time.time() - t_start) * 1000, 2)

    result = ReasoningResult(
        interpretation=raw["interpretation"],
        clinical_significance=raw["clinical_significance"],
        possible_conditions=raw["possible_conditions"],
        critical_flags=raw.get("critical_flags", []),
        confidence=raw["confidence"],
        citations=[],
        data_used=all_fields[:max_fields],
    )
    set_cache(cache_key, result.model_dump(), "reasoning")
    logger.info(
        "reasoning_service_complete",
        context_field_count=len(all_fields[:max_fields]),
        llm_latency_ms=llm_latency_ms,
    )
    return result
