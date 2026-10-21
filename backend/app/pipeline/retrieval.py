import threading
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from rank_bm25 import BM25Okapi
import logging

from app.core.config import settings
from app.pipeline.models import DocumentChunk, CitationInfo
from app.pipeline.embeddings import model_registry

logger = logging.getLogger(__name__)

class HybridRetrievalPipeline:
    """
    Thread-safe, multi-tenant hybrid retrieval pipeline combining:
    1. Dense semantic similarity search
    2. Sparse BM25 keyword matching
    3. Reciprocal Rank Fusion (RRF)
    4. Cross-Encoder reranking
    """
    def __init__(self):
        self._lock = threading.Lock()
        # Tenant partitioned store: {tenant_id: {"chunks": [...], "embeddings": np.ndarray, "bm25": BM25Okapi}}
        self._tenant_stores: Dict[str, Dict[str, Any]] = {}

    def _get_or_create_store(self, tenant_id: str) -> Dict[str, Any]:
        if tenant_id not in self._tenant_stores:
            self._tenant_stores[tenant_id] = {
                "chunks": [],
                "embeddings": np.empty((0, model_registry.dimension), dtype=np.float32),
                "bm25": None,
                "documents": {}
            }
        return self._tenant_stores[tenant_id]

    def index_chunks(self, chunks: List[DocumentChunk], tenant_id: str = "default") -> int:
        """
        Idempotently indexes document chunks for a specific tenant.
        Prevents duplicate chunks from skewing BM25 frequency or wasting vector space.
        """
        if not chunks:
            return 0

        with self._lock:
            store = self._get_or_create_store(tenant_id)
            existing_chunks: List[DocumentChunk] = store["chunks"]
            existing_ids = {c.chunk_id for c in existing_chunks}

            # Filter out chunks already indexed
            new_chunks = [c for c in chunks if c.chunk_id not in existing_ids]
            if not new_chunks:
                logger.info(f"All {len(chunks)} chunks already indexed for tenant '{tenant_id}'.")
                return 0

            # Encode new vectors
            encoder = model_registry.get_encoder()
            new_texts = [c.content for c in new_chunks]
            new_vectors = encoder.encode(new_texts, normalize_embeddings=True)

            # Update store
            updated_chunks = existing_chunks + new_chunks
            if store["embeddings"].shape[0] == 0:
                updated_embeddings = new_vectors
            else:
                updated_embeddings = np.vstack([store["embeddings"], new_vectors])

            # Track documents
            import time
            for c in new_chunks:
                if c.doc_hash not in store["documents"]:
                    store["documents"][c.doc_hash] = {
                        "filename": c.filename,
                        "doc_hash": c.doc_hash[:16],
                        "chunk_count": 0,
                        "created_at": time.time()
                    }
                store["documents"][c.doc_hash]["chunk_count"] += 1

            # Rebuild sparse BM25 index for the tenant
            tokenized_corpus = [c.content.lower().split() for c in updated_chunks]
            store["chunks"] = updated_chunks
            store["embeddings"] = updated_embeddings
            store["bm25"] = BM25Okapi(tokenized_corpus) if tokenized_corpus else None

            logger.info(
                f"Tenant '{tenant_id}': Indexed {len(new_chunks)} new chunks. "
                f"Total active chunks: {len(updated_chunks)}."
            )
            return len(new_chunks)

    def search(
        self, 
        query: str, 
        tenant_id: str = "default",
        top_k: int = 5, 
        rerank_top_k: int = 3
    ) -> Tuple[List[CitationInfo], np.ndarray]:
        """
        Executes dense + sparse search, merges via RRF, and applies Cross-Encoder reranking.
        """
        with self._lock:
            store = self._get_or_create_store(tenant_id)
            chunks: List[DocumentChunk] = store["chunks"]
            embeddings: np.ndarray = store["embeddings"]
            bm25 = store["bm25"]

        if not chunks or bm25 is None or embeddings.shape[0] == 0:
            logger.warning(f"Search aborted: Store for tenant '{tenant_id}' is empty.")
            return [], np.zeros((model_registry.dimension,), dtype=np.float32)

        # 1. Encode query
        encoder = model_registry.get_encoder()
        q_emb = encoder.encode([query], normalize_embeddings=True)[0]

        # 2. Dense Semantic Search
        dense_scores = np.dot(embeddings, q_emb)
        dense_rankings = np.argsort(dense_scores)[::-1]

        # 3. Sparse BM25 Search
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query) if tokenized_query else np.zeros(len(chunks))
        sparse_rankings = np.argsort(bm25_scores)[::-1]

        # 4. Reciprocal Rank Fusion (RRF)
        rrf_k = settings.RRF_K
        rrf_scores = {i: 0.0 for i in range(len(chunks))}

        effective_top = min(top_k * 2, len(chunks))
        for rank, doc_idx in enumerate(dense_rankings[:effective_top]):
            rrf_scores[doc_idx] += 1.0 / (rrf_k + rank + 1)
        for rank, doc_idx in enumerate(sparse_rankings[:effective_top]):
            rrf_scores[doc_idx] += 1.0 / (rrf_k + rank + 1)

        # Select top RRF candidates
        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        candidate_indices = [idx for idx, _ in sorted_candidates]

        # 5. Cross-Encoder Reranking
        reranker = model_registry.get_reranker()
        scored_candidates = []

        if reranker is not None and candidate_indices:
            pairs = [[query, chunks[i].content] for i in candidate_indices]
            try:
                cross_scores = reranker.predict(pairs)
                for i, score in zip(candidate_indices, cross_scores):
                    scored_candidates.append((chunks[i], float(score)))
                scored_candidates.sort(key=lambda x: x[1], reverse=True)
            except Exception as e:
                logger.warning(f"Reranking error ({e}). Falling back to RRF order.")
                scored_candidates = [(chunks[i], rrf_scores[i]) for i in candidate_indices]
        else:
            scored_candidates = [(chunks[i], rrf_scores[i]) for i in candidate_indices]

        # 6. Format Citations
        citations: List[CitationInfo] = []
        for rank, (chunk, score) in enumerate(scored_candidates[:rerank_top_k]):
            snippet_text = chunk.content[:200].strip() + ("..." if len(chunk.content) > 200 else "")
            citations.append(
                CitationInfo(
                    citation_id=rank + 1,
                    filename=chunk.filename,
                    page=chunk.primary_page,
                    bboxes=chunk.bboxes,
                    snippet=snippet_text,
                    rerank_score=round(float(score), 4)
                )
            )

        return citations, q_emb

    def get_chunk_count(self, tenant_id: str = "default") -> int:
        with self._lock:
            store = self._tenant_stores.get(tenant_id)
            return len(store["chunks"]) if store else 0

    def get_documents(self, tenant_id: str = "default") -> List[Dict[str, Any]]:
        with self._lock:
            store = self._tenant_stores.get(tenant_id)
            if not store or "documents" not in store:
                return []
            return list(store["documents"].values())

    def clear(self, tenant_id: Optional[str] = None):
        with self._lock:
            if tenant_id:
                self._tenant_stores.pop(tenant_id, None)
            else:
                self._tenant_stores.clear()

retrieval_pipe = HybridRetrievalPipeline()
