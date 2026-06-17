import time

from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

from pipeline_b.embedding.embedder import embed_single
from pipeline_b.schemas.input import PatientRecord
from pipeline_b.schemas.query import ParsedFilter
from pipeline_b.vector_db.qdrant_client import (
    COLLECTIONS,
    ensure_collections_exist,
    get_client,
    search_fields,
)
from shared.logger import get_logger


logger = get_logger(__name__)


def retrieve_by_filter(parsed: ParsedFilter) -> list[dict]:
    t_start = time.time()
    ensure_collections_exist()

    conditions = [
        FieldCondition(
            key="field_name",
            match=MatchValue(value=parsed.field_name),
        ),
        FieldCondition(
            key="source_type",
            match=MatchValue(value="patient"),
        ),
    ]

    if parsed.value is not None:
        if parsed.operator == "lt":
            conditions.append(
                FieldCondition(
                    key="numeric_value",
                    range=Range(lt=parsed.value),
                )
            )
        elif parsed.operator == "gt":
            conditions.append(
                FieldCondition(
                    key="numeric_value",
                    range=Range(gt=parsed.value),
                )
            )
        elif parsed.operator == "lte":
            conditions.append(
                FieldCondition(
                    key="numeric_value",
                    range=Range(lte=parsed.value),
                )
            )
        elif parsed.operator == "gte":
            conditions.append(
                FieldCondition(
                    key="numeric_value",
                    range=Range(gte=parsed.value),
                )
            )
        elif parsed.operator == "eq":
            conditions.append(
                FieldCondition(
                    key="numeric_value",
                    match=MatchValue(value=parsed.value),  # type: ignore
                )
            )

    query_filter = Filter(must=conditions)  # type: ignore
    client = get_client()
    results: list[dict] = []
    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTIONS["fields"],
            scroll_filter=query_filter,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        results.extend(point.payload for point in points if point.payload is not None)
        if offset is None:
            break

    logger.info(
        "retrieval_complete",
        retrieval_type="filter",
        result_count=len(results),
        field_name=parsed.field_name,
        operator=parsed.operator,
        duration_ms=round((time.time() - t_start) * 1000, 2),
    )
    return results


def retrieve_semantic(
    query: str,
    top_k: int = 10,
    patient_id: str | None = None,
) -> list[dict]:
    t_start = time.time()
    ensure_collections_exist()

    query_vector = embed_single(query)
    points = search_fields(
        query_vector=query_vector,
        top_k=top_k,
        patient_id=patient_id,
        source_type="patient",
    )
    results = [point.payload for point in points if point.payload is not None]

    logger.info(
        "retrieval_complete",
        retrieval_type="semantic",
        result_count=len(results),
        duration_ms=round((time.time() - t_start) * 1000, 2),
    )
    return results


def retrieve_for_patient(patient_id: str, db) -> list[PatientRecord]:
    from pipeline_b.adapters.pipeline_a_adapter import get_all_records_for_patient

    return get_all_records_for_patient(patient_id, db)
