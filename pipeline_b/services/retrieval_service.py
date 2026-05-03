from pipeline_b.cache.response_cache import get_cached, make_cache_key, set_cache
from pipeline_b.engines.intent_parser import parse_retrieval_intent
from pipeline_b.engines.retriever import retrieve_by_filter, retrieve_semantic
from pipeline_b.schemas.output import RetrievalResult
from pipeline_b.schemas.query import ClassifiedQuery
from shared.logger import get_logger


logger = get_logger(__name__)


def handle_retrieval_query(query: ClassifiedQuery, db) -> RetrievalResult:
    cache_key = make_cache_key(query.text, query.patient_id, "retrieval")
    cached = get_cached(cache_key)
    if cached:
        result = RetrievalResult(**cached)
        logger.info(
            "retrieval_service_complete",
            retrieval_type=result.retrieval_type,
            result_count=result.total_count,
            cached=True,
        )
        return result

    parsed = parse_retrieval_intent(query.text)
    if parsed.operator == "any":
        results = retrieve_semantic(query.text, patient_id=query.patient_id)
        retrieval_type = "semantic"
    else:
        results = retrieve_by_filter(parsed)
        retrieval_type = "filter"

    result = RetrievalResult(
        records=results,
        total_count=len(results),
        query_interpretation=f"{parsed.field_name} {parsed.operator} {parsed.value}",
        retrieval_type=retrieval_type,
    )
    set_cache(cache_key, result.model_dump(), "retrieval")
    logger.info(
        "retrieval_service_complete",
        retrieval_type=retrieval_type,
        result_count=len(results),
        cached=False,
    )
    return result
