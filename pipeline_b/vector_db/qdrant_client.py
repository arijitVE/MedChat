import atexit

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    Range,
    VectorParams,
)

from pipeline_b.chunking.chunker import QdrantChunk
from shared.config import get_settings


COLLECTIONS = {"fields": "hdmis_fields", "documents": "hdmis_documents"}
VECTOR_SIZE = 384

_client: QdrantClient | None = None


def _close_client() -> None:
    global _client

    if _client is not None:
        _client.close()
        _client = None


atexit.register(_close_client)


def get_client() -> QdrantClient:
    global _client

    if _client is None:
        settings = get_settings()
        if settings.QDRANT_URL:
            _client = QdrantClient(url=settings.QDRANT_URL)
        else:
            _client = QdrantClient(path=settings.QDRANT_STORAGE_PATH)
    return _client


def ensure_collections_exist():
    client = get_client()
    for name in COLLECTIONS.values():
        if not client.collection_exists(name):
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )


def upsert_chunks(
    chunks: list[QdrantChunk],
    vectors: list[list[float]],
    collection: str,
):
    client = get_client()
    points = [
        PointStruct(id=int(chunk.chunk_id), vector=vec, payload=chunk.payload)
        for chunk, vec in zip(chunks, vectors)
    ]
    client.upsert(collection_name=COLLECTIONS[collection], points=points)


def search_fields(
    query_vector: list[float],
    top_k: int = 10,
    patient_id: str | None = None,
    document_type: str | None = None,
    source_type: str = "patient",
    is_abnormal: bool | None = None,
    field_name: str | None = None,
    numeric_value_lt: float | None = None,
    numeric_value_gt: float | None = None,
) -> list:
    conditions = []

    if patient_id is not None:
        conditions.append(
            FieldCondition(key="patient_id", match=MatchValue(value=patient_id))
        )
    if document_type is not None:
        conditions.append(
            FieldCondition(key="document_type", match=MatchValue(value=document_type))
        )
    if source_type is not None:
        conditions.append(
            FieldCondition(key="source_type", match=MatchValue(value=source_type))
        )
    if is_abnormal is not None:
        conditions.append(
            FieldCondition(key="is_abnormal", match=MatchValue(value=is_abnormal))
        )
    if field_name is not None:
        conditions.append(
            FieldCondition(key="field_name", match=MatchValue(value=field_name))
        )
    if numeric_value_lt is not None or numeric_value_gt is not None:
        conditions.append(
            FieldCondition(
                key="numeric_value",
                range=Range(lt=numeric_value_lt, gt=numeric_value_gt),
            )
        )

    query_filter = Filter(must=conditions) if conditions else None
    client = get_client()
    if hasattr(client, "search"):
        return client.search(
            collection_name=COLLECTIONS["fields"],
            query_vector=query_vector,
            query_filter=query_filter,
            limit=top_k,
        )

    return client.query_points(
        collection_name=COLLECTIONS["fields"],
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
    ).points


def get_patient_field_history(patient_id: str, field_name: str) -> list[dict]:
    client = get_client()
    query_filter = Filter(
        must=[
            FieldCondition(key="patient_id", match=MatchValue(value=patient_id)),
            FieldCondition(key="field_name", match=MatchValue(value=field_name)),
        ]
    )

    records = []
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
        records.extend(point.payload for point in points if point.payload is not None)
        if offset is None:
            break

    return sorted(records, key=lambda payload: payload.get("collection_date") or "")
