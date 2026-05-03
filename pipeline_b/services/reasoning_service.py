import time

from pipeline_b.adapters.pipeline_a_adapter import get_all_records_for_patient
from pipeline_b.cache.response_cache import get_cached, make_cache_key, set_cache
from pipeline_b.engines.generator import generate_doctor_reasoning
from pipeline_b.schemas.output import ReasoningResult
from pipeline_b.schemas.query import ClassifiedQuery
from shared.logger import get_logger


logger = get_logger(__name__)


def handle_reasoning_query(
    query: ClassifiedQuery,
    patient_id: str,
    db,
) -> ReasoningResult:
    cache_key = make_cache_key(query.text, patient_id, "reasoning")
    cached = get_cached(cache_key)
    if cached:
        return ReasoningResult(**{**cached, "cached": True})

    records = get_all_records_for_patient(patient_id, db)
    all_fields = [f for r in records for f in r.fields]

    t_start = time.time()
    raw = generate_doctor_reasoning(all_fields, query.text)
    llm_latency_ms = round((time.time() - t_start) * 1000, 2)

    result = ReasoningResult(
        interpretation=raw["interpretation"],
        clinical_significance=raw["clinical_significance"],
        possible_conditions=raw["possible_conditions"],
        critical_flags=raw.get("critical_flags", []),
        confidence=raw["confidence"],
        citations=[],
        data_used=all_fields[:15],
    )
    set_cache(cache_key, result.model_dump(), "reasoning")
    logger.info(
        "reasoning_service_complete",
        context_field_count=len(all_fields[:15]),
        llm_latency_ms=llm_latency_ms,
    )
    return result
