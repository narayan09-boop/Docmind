import time
import numpy as np
from app.core.cache import SemanticCache

def test_semantic_cache_hit_and_miss():
    cache = SemanticCache(similarity_threshold=0.85)
    vec1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec_similar = np.array([0.95, 0.1, 0.0], dtype=np.float32)
    vec_different = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    cache.set("What is revenue?", vec1, {"answer": "Revenue is $4.2B"}, tenant_id="t1")

    # Hit
    hit = cache.get(vec_similar, tenant_id="t1")
    assert hit is not None
    assert hit["is_cached"] is True
    assert hit["answer"] == "Revenue is $4.2B"

    # Miss due to low similarity
    miss = cache.get(vec_different, tenant_id="t1")
    assert miss is None

def test_cache_tenant_isolation():
    cache = SemanticCache(similarity_threshold=0.85)
    vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    cache.set("Secret data", vec, {"answer": "Tenant 1 secret answer"}, tenant_id="tenant_1")

    # Same vector queried by tenant_2 should miss
    res_t2 = cache.get(vec, tenant_id="tenant_2")
    assert res_t2 is None

    # Queried by tenant_1 should hit
    res_t1 = cache.get(vec, tenant_id="tenant_1")
    assert res_t1 is not None

def test_cache_ttl_expiration():
    cache = SemanticCache(similarity_threshold=0.85, ttl_seconds=1)
    vec = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    cache.set("Query", vec, {"answer": "Val"}, tenant_id="t1")

    # Manually age entry
    cache._tenant_cache["t1"][0]["timestamp"] = time.time() - 10

    # Querying should expire and return None
    res = cache.get(vec, tenant_id="t1")
    assert res is None
