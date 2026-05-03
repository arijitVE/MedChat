from pipeline_b.cache import response_cache


def test_cache_key_deterministic():
    key1 = response_cache.make_cache_key("query", "patient-1", "retrieval")
    key2 = response_cache.make_cache_key("query", "patient-1", "retrieval")

    assert key1 == key2


def test_cache_hit_returns_cached():
    key = response_cache.make_cache_key("query", "patient-1", "retrieval")
    response_cache.set_cache(key, {"ok": True}, "retrieval")

    assert response_cache.get_cached(key) == {"ok": True}


def test_cache_miss_returns_none():
    assert response_cache.get_cached("missing") is None


def test_invalidate_patient_clears_entries():
    key = response_cache.make_cache_key("query", "patient-1", "retrieval")
    response_cache.set_cache(key, {"ok": True}, "retrieval")

    response_cache.invalidate_patient("patient-1")

    assert response_cache.get_cached(key) is None
    assert response_cache._cache == {}
