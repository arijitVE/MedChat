import hashlib
from datetime import datetime, timezone

from pipeline_b.schemas.output import CachedResponse


_cache: dict[str, CachedResponse] = {}


def make_cache_key(query: str, patient_id: str | None, query_type: str) -> str:
    raw = f"{query}|{patient_id}|{query_type}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached(cache_key: str) -> dict | None:
    entry = _cache.get(cache_key)
    if entry is None:
        return None
    return entry.result


def set_cache(
    cache_key: str,
    result: dict,
    query_type: str,
    ttl_seconds: int = 300,
):
    _cache[cache_key] = CachedResponse(
        cache_key=cache_key,
        result=result,
        created_at=datetime.now(timezone.utc),
        query_type=query_type,
    )


def invalidate_patient(patient_id: str):
    global _cache

    before = len(_cache)
    _cache = {}
    from shared.logger import get_logger

    get_logger(__name__).info(
        "cache_invalidated",
        patient_id=patient_id,
        entries_cleared=before,
    )
