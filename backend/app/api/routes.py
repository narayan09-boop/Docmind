from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time

from app.pipeline.ingestion import DocumentIngestionPipeline
from app.pipeline.retrieval import HybridRetrievalPipeline
from app.pipeline.generator import GroundedGenerationPipeline
from app.core.cache import semantic_cache
from app.eval.benchmark import eval_harness

router = APIRouter()

# Singletons for memory-resident pipeline
ingestion_pipe = DocumentIngestionPipeline()
retrieval_pipe = HybridRetrievalPipeline()
generator_pipe = GroundedGenerationPipeline()

# In-memory document storage for preview
DOC_CATALOG: Dict[str, Any] = {
    "uploaded_files": [],
    "total_chunks": 0
}

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    rerank_top_k: Optional[int] = 3

class QueryResponse(BaseModel):
    query: str
    answer: str
    is_cached: bool
    similarity_score: Optional[float] = None
    latency_ms: float
    citations: List[Dict[str, Any]]

@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Parses PDF layout, extracts tables/bounding boxes, runs semantic chunking,
    and indexes into Hybrid Dense+BM25 vector space.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")
    
    start_t = time.perf_counter()
    file_bytes = await file.read()
    
    # 1. Layout Extraction & Bounding Boxes
    elements = ingestion_pipe.extract_document_elements(file_bytes, file.filename)
    
    # 2. Semantic Chunking
    chunks = ingestion_pipe.semantic_chunking(elements)
    
    # 3. Hybrid Indexing
    retrieval_pipe.index_chunks(chunks)
    
    elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
    
    DOC_CATALOG["uploaded_files"].append(file.filename)
    DOC_CATALOG["total_chunks"] += len(chunks)

    return {
        "status": "success",
        "filename": file.filename,
        "elements_extracted": len(elements),
        "chunks_indexed": len(chunks),
        "indexing_latency_ms": elapsed_ms,
        "sample_preview": chunks[:2] if chunks else []
    }

@router.post("/query", response_model=QueryResponse)
async def query_pipeline(payload: QueryRequest):
    """
    Standard query with Semantic Caching, Hybrid Retrieval, and Cross-Encoder Reranking.
    """
    start_t = time.perf_counter()

    # 1. Retrieval & Query Vector
    retrieved_chunks, q_vector = retrieval_pipe.search(
        query=payload.query,
        top_k=payload.top_k,
        rerank_top_k=payload.rerank_top_k
    )

    # 2. Check Semantic Cache
    cached_hit = semantic_cache.get(q_vector)
    if cached_hit:
        cached_hit["latency_ms"] = round((time.perf_counter() - start_t) * 1000, 2)
        return QueryResponse(**cached_hit)

    # 3. Format Citations
    citations = [
        {
            "citation_id": i + 1,
            "filename": c.get("filename"),
            "page": c.get("primary_page"),
            "bboxes": c.get("bboxes", []),
            "snippet": c.get("content")[:180] + "...",
            "rerank_score": round(c.get("rerank_score", 0.0), 3)
        }
        for i, c in enumerate(retrieved_chunks)
    ]

    # Synthesize answer
    answer_text = (
        f"Grounded synthesis: Document evidence from {citations[0]['filename']} indicates that "
        f"{retrieved_chunks[0]['content'][:140]}... [Citation 1, Page {citations[0]['page']}]."
        if citations else "No relevant information found in the knowledge base."
    )

    elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

    response_data = {
        "query": payload.query,
        "answer": answer_text,
        "is_cached": False,
        "similarity_score": 1.0,
        "latency_ms": elapsed_ms,
        "citations": citations
    }

    # Store in semantic cache
    semantic_cache.set(payload.query, q_vector, response_data)

    return QueryResponse(**response_data)

@router.post("/stream")
async def stream_query(payload: QueryRequest):
    """
    Streams response tokens using Server-Sent Events (SSE), immediately emitting citations
    metadata followed by token stream.
    """
    retrieved_chunks, _ = retrieval_pipe.search(
        query=payload.query,
        top_k=payload.top_k,
        rerank_top_k=payload.rerank_top_k
    )

    return StreamingResponse(
        generator_pipe.stream_generation(payload.query, retrieved_chunks),
        media_type="text/event-stream"
    )

@router.get("/eval/benchmark")
async def get_benchmarks():
    """
    Runs quantitative benchmark comparisons: Hit Rate@K, MRR, Faithfulness,
    and chunking strategy A/B test simulation.
    """
    return eval_harness.benchmark_chunking_strategies(sample_text="Evaluation Corpus")

@router.get("/stats")
async def get_stats():
    return {
        "catalog": DOC_CATALOG,
        "cache_entries": len(semantic_cache._cache),
        "status": "ready"
    }
