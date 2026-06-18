# pipeline_b/vector_db/qdrant_client.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from shared.config import get_settings

COLLECTIONS = {
    "raw_chunks": "raw_chunks",
    "structured_medical_data": "structured_medical_data"
}
VECTOR_SIZE = 384

_client = None

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

def upsert_vectors(collection: str, points: list[PointStruct]):
    if not points: return
    client = get_client()
    client.upsert(collection_name=COLLECTIONS[collection], points=points)

def search(collection: str, query_vector: list[float], case_id: str, limit: int = 5):
    client = get_client()
    query_filter = Filter(
        must=[
            FieldCondition(key="case_id", match=MatchValue(value=case_id))
        ]
    )
    if hasattr(client, "search"):
        return client.search(
            collection_name=COLLECTIONS[collection],
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
        )
    return client.query_points(
        collection_name=COLLECTIONS[collection],
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
    ).points
