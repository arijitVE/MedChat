from pipeline_b.cache.response_cache import get_cached, make_cache_key, set_cache
from pipeline_b.engines.intent_parser import parse_retrieval_intent
from pipeline_b.engines.trend_analyzer import analyze_trend
from pipeline_b.schemas.output import TrendResult
from pipeline_b.schemas.query import ClassifiedQuery
from shared.logger import get_logger
from shared.utils.medical_dict import MEDICAL_SYNONYMS


logger = get_logger(__name__)


def _extract_field_name(query_text: str) -> str:
    query_lower = query_text.strip().lower()
    canonical_names = set(MEDICAL_SYNONYMS.values())
    for name in sorted(canonical_names, key=len, reverse=True):
        if name in query_lower:
            return name
    for raw, canonical in sorted(MEDICAL_SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True):
        if raw in query_lower:
            return canonical

    return parse_retrieval_intent(query_text).field_name


def handle_trend_query(
    query: ClassifiedQuery,
    patient_id: str,
    db,
) -> TrendResult:
    cache_key = make_cache_key(query.text, patient_id, "trend")
    cached = get_cached(cache_key)
    if cached:
        return TrendResult(**{**cached, "cached": True})

    field_name = _extract_field_name(query.text)
    result = analyze_trend(patient_id, field_name)
    set_cache(cache_key, result.model_dump(), "trend")
    logger.info(
        "trend_service_complete",
        field_name=field_name,
        patient_id=patient_id,
        trend_direction=result.trend_direction,
        cached=False,
    )
    return result
