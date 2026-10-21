import numpy as np
from typing import List, Dict, Any, Tuple
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
import logging

logger = logging.getLogger(__name__)

class HybridRetrievalPipeline:
    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        logger.info("Initializing Hybrid Retrieval & Cross-Encoder models...")
        self.encoder = SentenceTransformer(embedding_model)
        self.reranker = CrossEncoder(reranker_model)
        self.chunks: List[Dict[str, Any]] = []
        self.dense_embeddings: np.ndarray = np.empty((0, 384))
        self.bm25: BM25Okapi = None

    def index_chunks(self, chunks: List[Dict[str, Any]]):
        """Builds both dense vector space and sparse BM25 index."""
        if not chunks:
            return

        self.chunks = chunks
        corpus_texts = [c["content"] for c in chunks]

        # 1. Dense Embeddings
        self.dense_embeddings = self.encoder.encode(corpus_texts, normalize_embeddings=True)

        # 2. Sparse BM25 Index
        tokenized_corpus = [doc.lower().split(" ") for doc in corpus_texts]
        self.bm25 = BM25Okapi(tokenized_corpus)
        logger.info(f"Indexed {len(chunks)} chunks into Hybrid Vector+BM25 Store.")

    def search(
        self, 
        query: str, 
        top_k: int = 10, 
        rerank_top_k: int = 3,
        rrf_k: int = 60
    ) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        """
        Executes:
        1. Dense semantic search
        2. Sparse BM25 search
        3. Reciprocal Rank Fusion (RRF)
        4. Cross-Encoder reranking
        Returns reranked chunks with citation coordinates and the query embedding vector.
        """
        if not self.chunks or self.bm25 is None:
            return [], np.zeros((384,))

        # Query embedding
        q_emb = self.encoder.encode([query], normalize_embeddings=True)[0]

        # 1. Dense Scoring
        dense_scores = np.dot(self.dense_embeddings, q_emb)
        dense_rankings = np.argsort(dense_scores)[::-1]

        # 2. Sparse BM25 Scoring
        tokenized_query = query.lower().split(" ")
        bm25_scores = self.bm25.get_scores(tokenized_query)
        sparse_rankings = np.argsort(bm25_scores)[::-1]

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = {i: 0.0 for i in range(len(self.chunks))}
        for rank, doc_idx in enumerate(dense_rankings[:top_k]):
            rrf_scores[doc_idx] += 1.0 / (rrf_k + rank + 1)
        for rank, doc_idx in enumerate(sparse_rankings[:top_k]):
            rrf_scores[doc_idx] += 1.0 / (rrf_k + rank + 1)

        # Select candidates for reranking
        sorted_candidates = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        candidate_indices = [idx for idx, _ in sorted_candidates]

        # 4. Cross-Encoder Reranking
        pairs = [[query, self.chunks[i]["content"]] for i in candidate_indices]
        cross_scores = self.reranker.predict(pairs)

        # Pair candidates with cross-encoder scores
        ranked_results = []
        for i, score in zip(candidate_indices, cross_scores):
            chunk_copy = self.chunks[i].copy()
            chunk_copy["rerank_score"] = float(score)
            ranked_results.append(chunk_copy)

        # Sort by reranker score descending
        ranked_results.sort(key=lambda x: x["rerank_score"], reverse=True)
        return ranked_results[:rerank_top_k], q_emb
