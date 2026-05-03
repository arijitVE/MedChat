import pytest


@pytest.fixture(autouse=True)
def clear_pipeline_b_cache():
    from pipeline_b.cache import response_cache

    response_cache._cache = {}
    yield
    response_cache._cache = {}
