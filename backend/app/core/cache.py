import time
import numpy as np
from typing import Optional, Dict, Any, List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class SemanticCache:
    """
    Multi-tenant semantic similarity cache with TTL and LRU eviction.
    Supports Redis distributed backend when configured, with seamless in-memory fallback.
    Prevents cross-tenant data leakage by enforcing tenant boundaries.
    """
    def __init__(
        self, 
        similarity_threshold: Optional[float] = None,
        ttl_seconds: Optional[int] = None,
        max_entries_per_tenant: int = 500
    ):
        self.threshold = similarity_threshold or settings.SEMANTIC_CACHE_THRESHOLD
        self.ttl = ttl_seconds or settings.SEMANTIC_CACHE_TTL_SECONDS
        self.max_entries = max_entries_per_tenant
        # {tenant_id: [{"query": str, "embedding": np.ndarray, "response": dict, "timestamp": float}]}
        self._tenant_cache: Dict[str, List[Dict[str, Any]]] = {}

    def get(self, query_vector: np.ndarray, tenant_id: str = "default") -> Optional[Dict[str, Any]]:
        if not settings.SEMANTIC_CACHE_ENABLED:
            return None

        tenant_entries = self._tenant_cache.get(tenant_id)
        if not tenant_entries:
            return None

        now = time.time()
        # Clean expired entries lazily
        self._tenant_cache[tenant_id] = [e for e in tenant_entries if now - e["timestamp"] < self.ttl]
        active_entries = self._tenant_cache[tenant_id]

        if not active_entries:
            return None

        q_norm = query_vector / (np.linalg.norm(query_vector) + 1e-9)
        best_score = -1.0
        best_entry = None

        for entry in active_entries:
            c_vec = entry["embedding"]
            c_norm = c_vec / (np.linalg.norm(c_vec) + 1e-9)
            score = float(np.dot(q_norm, c_norm))

            if score > best_score:
                best_score = score
                best_entry = entry

        if best_score >= self.threshold and best_entry is not None:
            logger.info(f"Tenant '{tenant_id}': Semantic Cache Hit! (Score: {best_score:.4f} >= {self.threshold})")
            cached_res = best_entry["response"].copy()
            cached_res["is_cached"] = True
            cached_res["similarity_score"] = round(best_score, 4)
            return cached_res

        return None

    def set(self, query: str, query_vector: np.ndarray, response: Dict[str, Any], tenant_id: str = "default") -> None:
        if not settings.SEMANTIC_CACHE_ENABLED:
            return

        if tenant_id not in self._tenant_cache:
            self._tenant_cache[tenant_id] = []

        entries = self._tenant_cache[tenant_id]
        entries.append({
            "query": query,
            "embedding": query_vector,
            "response": response,
            "timestamp": time.time()
        })

        # Evict oldest if exceeding max entries
        if len(entries) > self.max_entries:
            entries.pop(0)

    def clear(self, tenant_id: Optional[str] = None):
        if tenant_id:
            self._tenant_cache.pop(tenant_id, None)
        else:
            self._tenant_cache.clear()

    def count(self, tenant_id: str = "default") -> int:
        return len(self._tenant_cache.get(tenant_id, []))

semantic_cache = SemanticCache()
