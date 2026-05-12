import time
import json

from pipeline_b.adapters.pipeline_a_adapter import get_all_records_for_patient
from pipeline_b.cache.response_cache import get_cached, make_cache_key, set_cache
from pipeline_b.engines.generator import generate_patient_explanation
from pipeline_b.schemas.input import PatientRecord
from pipeline_b.schemas.output import PatientChatResult
from pipeline_b.schemas.query import ClassifiedQuery
from shared.logger import get_logger


logger = get_logger(__name__)


BLOCKED_TERMS = [
    "diagnosis",
    "diagnose",
    "prescribe",
    "prescription",
    "medication",
    "drug",
    "treatment",
    "cancer",
    "tumor",
    "surgery",
    "operate",
    "cure",
    "medicine",
]


DISCLAIMER = (
    "This explanation is for informational purposes only and does not "
    "constitute medical advice. Please consult your doctor for "
    "interpretation and treatment decisions."
)


def _filter_records(records: list[PatientRecord], filters: dict | None) -> list[PatientRecord]:
    if not filters:
        return records

    job_ids = filters.get("job_ids")
    if isinstance(job_ids, list):
        allowed_job_ids = {str(job_id) for job_id in job_ids}
        return [record for record in records if record.job_id in allowed_job_ids]

    return records


def _plain_english_status(is_abnormal: bool | None) -> str:
    if is_abnormal is True:
        return "Outside normal range"
    if is_abnormal is False:
        return "Within normal range"
    return "See doctor"


def handle_patient_query(
    query: ClassifiedQuery,
    patient_id: str,
    db,
) -> PatientChatResult:
    blocked = any(term in query.text.lower() for term in BLOCKED_TERMS)
    if blocked:
        logger.info(
            "patient_query_complete",
            safety_blocked=True,
            llm_latency_ms=0,
        )
        return PatientChatResult(
            response="For questions about treatment or diagnosis, please consult your doctor.",
            simplified_fields=[],
            disclaimer=DISCLAIMER,
            safety_blocked=True,
        )

    cache_text = f"{query.text}|filters={json.dumps(query.filters or {}, sort_keys=True)}"
    cache_key = make_cache_key(cache_text, patient_id, "patient_chat")
    cached = get_cached(cache_key)
    if cached:
        return PatientChatResult(**cached)

    records = _filter_records(get_all_records_for_patient(patient_id, db), query.filters)
    all_fields = [f for r in records for f in r.fields]

    t_start = time.time()
    raw = generate_patient_explanation(all_fields, query.text)
    llm_latency_ms = round((time.time() - t_start) * 1000, 2)

    simplified_fields = [
        {
            "name": f.name,
            "value": f.value,
            "status": _plain_english_status(f.is_abnormal),
        }
        for f in all_fields[:10]
    ]

    result = PatientChatResult(
        response=raw["response"],
        simplified_fields=simplified_fields,
        disclaimer=DISCLAIMER,
        safety_blocked=False,
    )
    set_cache(cache_key, result.model_dump(), "patient_chat")
    logger.info(
        "patient_query_complete",
        safety_blocked=False,
        llm_latency_ms=llm_latency_ms,
    )
    return result
