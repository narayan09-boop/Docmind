# DocMind Architecture Specification

## 1. System Overview

DocMind is a multi-tenant, multimodal knowledge copilot and enterprise Retrieval-Augmented Generation (RAG) platform. The platform is architected to eliminate common RAG failure modes (hallucinations, loss of tabular layout context, and unbounded inference latency) through layout-aware layout parsing, hybrid retrieval, cross-encoder reranking, and verified bounding-box citation grounding.

```
                    ┌────────────────────────────┐
                    │    Next.js 14 Frontend     │
                    │  (Dual-Pane UI & Citations)│
                    └─────────────┬──────────────┘
                                  │ HTTPS / SSE
                                  ▼
                    ┌────────────────────────────┐
                    │       FastAPI Gateway      │
                    │  (Auth, Rate Limit, CORS)  │
                    └─────────────┬──────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
┌───────────────────────┐                        ┌───────────────────────┐
│ Ingestion Pipeline    │                        │ Query & Search Engine │
│ - PDF Layout Analyzer │                        │ - Semantic Cache      │
│ - Content Hashing     │                        │ - Dense Vector Index  │
│ - Semantic Chunker    │                        │ - Sparse BM25 Index   │
└───────────┬───────────┘                        │ - RRF Fusion & Rerank │
            │                                    └───────────┬───────────┘
            ▼                                                │
┌───────────────────────┐                                    ▼
│ Tenant Vector Space   │◄───────────────────────────────────┘
│ & Storage Layer       │
└───────────────────────┘
```

---

## 2. Component Design & Responsibilities

### Ingestion & Parsing (`app/pipeline/ingestion.py`)
- **Validation**: Enforces magic bytes check (`%PDF-1.4+`) and file size limits (`MAX_UPLOAD_SIZE_BYTES`).
- **Content Hashing**: Computes SHA-256 hash over raw document bytes. Used for deduplication and idempotent index updates.
- **Layout Analysis**: PyMuPDF extracts text blocks, tables, and exact page bounding boxes `[x0, y0, x1, y1]`.
- **Semantic Boundary Chunking**: Computes cosine distances between adjacent sentence embeddings. Breaks are placed at distance drops exceeding the configurable percentile threshold (default: 85th percentile), preserving complete tabular spans.

### Hybrid Retrieval & Reranking (`app/pipeline/retrieval.py`)
- **Dense Vector Search**: Generates normalized dense embeddings using `all-MiniLM-L6-v2` (dimension: 384).
- **Sparse Keyword Search**: BM25Okapi inverted index per tenant.
- **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse lists using constant $k=60$:
  $$RRF(d) = \frac{1}{60 + \text{rank}_{dense}(d)} + \frac{1}{60 + \text{rank}_{sparse}(d)}$$
- **Cross-Encoder Reranking**: Re-scores top RRF candidates using `cross-encoder/ms-marco-MiniLM-L-6-v2` to evaluate query-document semantic relevance.

### Semantic Caching (`app/core/cache.py`)
- Multi-tenant partitioning: Cache keys and similarity comparisons are scoped strictly by `tenant_id`.
- Cosine similarity threshold (default: $\ge 0.90$).
- Time-to-Live (TTL: 24h) and LRU capacity pruning (max 500 entries/tenant).

### Generative Inference (`app/pipeline/generator.py`)
- **Prompt Injection Defense**: Untrusted retrieved excerpts are encapsulated in `<untrusted_document_context>` XML tags with strict anti-injection system directives.
- **Streaming SSE**: Emits citation coordinate metadata first, followed by token streaming.
- **Pluggable LLM**: Supports OpenAI streaming or local deterministic synthesis.

---

## 3. Architectural Invariants vs. Configurable Parameters

| Parameter | Type | Default | Justification |
| :--- | :--- | :--- | :--- |
| `RRF_K` | Configurable | `60` | Industry standard smoothing constant; avoids scale mismatch between BM25 scores and cosine similarities. |
| `SEMANTIC_CACHE_THRESHOLD` | Configurable | `0.90` | Empirically validated sweet spot balancing latency savings with accuracy. |
| `MAX_UPLOAD_SIZE_BYTES` | Configurable | `15MB` | Protects parsing thread from out-of-memory exhaustion. |
| `DOC_HASH_ALGO` | Invariant | `SHA-256` | Collision resistance required for document deduplication and index provenance. |
