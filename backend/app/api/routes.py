import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import verify_auth, sanitize_filename
from app.core.cache import semantic_cache
from app.pipeline.ingestion import DocumentIngestionPipeline
from app.pipeline.retrieval import retrieval_pipe
from app.pipeline.generator import generator_pipe
from app.eval.benchmark import eval_harness

router = APIRouter()
ingestion_pipe = DocumentIngestionPipeline()

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="User search query")
    top_k: Optional[int] = Field(default=5, ge=1, le=20)
    rerank_top_k: Optional[int] = Field(default=3, ge=1, le=10)

class QueryResponse(BaseModel):
    query: str
    answer: str
    is_cached: bool
    similarity_score: Optional[float] = None
    latency_ms: float
    citations: List[Dict[str, Any]]
    tenant_id: str

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_document(
    file: UploadFile = File(...),
    tenant_id: str = Depends(verify_auth)
):
    """
    Parses PDF layout, validates magic bytes and file size, performs semantic chunking,
    and idempotently indexes into tenant-isolated hybrid vector store.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF documents (.pdf) are accepted."
        )

    safe_name = sanitize_filename(file.filename)
    start_t = time.perf_counter()

    try:
        file_bytes = await file.read()
        # Ingestion pipeline validates size, magic bytes, parses elements
        elements = ingestion_pipe.extract_document_elements(file_bytes, safe_name)
        doc_hash = ingestion_pipe.compute_hash(file_bytes)
        
        # Chunking
        chunks = ingestion_pipe.semantic_chunking(
            elements=elements,
            filename=safe_name,
            doc_hash=doc_hash,
            tenant_id=tenant_id
        )

        # Idempotent Indexing
        indexed_count = retrieval_pipe.index_chunks(chunks, tenant_id=tenant_id)
        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

        return {
            "status": "success",
            "filename": safe_name,
            "doc_hash": doc_hash[:16],
            "tenant_id": tenant_id,
            "elements_extracted": len(elements),
            "chunks_generated": len(chunks),
            "new_chunks_indexed": indexed_count,
            "indexing_latency_ms": elapsed_ms
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document processing failed due to an internal error."
        )

@router.post("/query", response_model=QueryResponse)
async def query_pipeline(
    payload: QueryRequest,
    tenant_id: str = Depends(verify_auth)
):
    """
    Query execution with semantic cache check, hybrid retrieval, and grounded response.
    """
    start_t = time.perf_counter()

    # 1. Hybrid Retrieval & Query Embedding
    citations, q_vector = retrieval_pipe.search(
        query=payload.query,
        tenant_id=tenant_id,
        top_k=payload.top_k,
        rerank_top_k=payload.rerank_top_k
    )

    # 2. Semantic Cache Check (Tenant-Isolated)
    cached_hit = semantic_cache.get(q_vector, tenant_id=tenant_id)
    if cached_hit:
        cached_hit["latency_ms"] = round((time.perf_counter() - start_t) * 1000, 2)
        return QueryResponse(**cached_hit)

    # 3. Format Citations
    citations_data = [c.model_dump() for c in citations]

    # Synthesize answer
    if citations:
        answer_text = (
            f"Based on evidence from {citations[0].filename}, the document indicates: "
            f"\"{citations[0].snippet}\" [Citation 1, Page {citations[0].page}]."
        )
    else:
        answer_text = "Insufficient document context in knowledge base to answer this query."

    elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

    response_data = {
        "query": payload.query,
        "answer": answer_text,
        "is_cached": False,
        "similarity_score": 1.0,
        "latency_ms": elapsed_ms,
        "citations": citations_data,
        "tenant_id": tenant_id
    }

    # Populate cache
    semantic_cache.set(payload.query, q_vector, response_data, tenant_id=tenant_id)

    return QueryResponse(**response_data)

@router.post("/stream")
async def stream_query(
    payload: QueryRequest,
    tenant_id: str = Depends(verify_auth)
):
    """
    Streams response tokens as Server-Sent Events (SSE) with prompt injection defense.
    """
    citations, _ = retrieval_pipe.search(
        query=payload.query,
        tenant_id=tenant_id,
        top_k=payload.top_k,
        rerank_top_k=payload.rerank_top_k
    )

    return StreamingResponse(
        generator_pipe.stream_generation(payload.query, citations),
        media_type="text/event-stream"
    )

@router.get("/eval/benchmark")
async def run_evaluations(tenant_id: str = Depends(verify_auth)):
    """
    Runs automated dataset-driven evaluation benchmark tracking Hit Rate@K, MRR,
    Faithfulness, and latency percentiles.
    """
    try:
        summary = eval_harness.run_benchmark()
        return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation execution failed: {str(e)}"
        )

@router.get("/stats")
async def get_system_stats(tenant_id: str = Depends(verify_auth)):
    return {
        "tenant_id": tenant_id,
        "indexed_chunks": retrieval_pipe.get_chunk_count(tenant_id=tenant_id),
        "cached_queries": semantic_cache.count(tenant_id=tenant_id),
        "embedding_model": settings.EMBEDDING_MODEL_NAME,
        "reranker_model": settings.RERANKER_MODEL_NAME,
        "status": "operational"
    }
