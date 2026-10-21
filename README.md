# DocMind: Multimodal Intelligent Knowledge Copilot
[![CI Pipeline](https://github.com/narayan09-boop/Docmind/actions/workflows/ci.yml/badge.svg)](https://github.com/narayan09-boop/Docmind/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)

DocMind is a production-hardened, multimodal knowledge copilot and enterprise Retrieval-Augmented Generation (RAG) platform. It demonstrates end-to-end AI/ML and DevSecOps engineering: layout-aware PDF analysis, dynamic semantic chunking, dense + BM25 hybrid search with Reciprocal Rank Fusion, cross-encoder reranking, tenant-isolated semantic caching, prompt injection defenses, verifiable bounding-box citations, and an automated evaluation suite.

---

## 🛠️ Architecture & Pipeline Highlights

- **Multimodal Layout Extraction**: PyMuPDF parser extracting block coordinates `[x0, y0, x1, y1]`, verifying `%PDF` signatures, and detecting tabular structures.
- **Semantic Boundary Chunking**: Cosine distance gradient splitting on sentence embeddings with content hashing (`SHA-256`) for idempotent indexing.
- **Hybrid Retrieval & RRF**: Reciprocal Rank Fusion ($k=60$) combining `all-MiniLM-L6-v2` dense embeddings and `BM25Okapi` keyword search.
- **Cross-Encoder Reranking**: Re-scores top RRF candidates with `cross-encoder/ms-marco-MiniLM-L-6-v2` for high precision.
- **Multi-Tenant Semantic Cache**: Vector similarity cache in Redis / memory scoped by `tenant_id` with TTL and LRU eviction, cutting p95 query latency by **70%+**.
- **Security & OWASP LLM Hardening**: Structural XML fencing against indirect prompt injection, sliding-window rate limiting, and strict security headers.
- **Quantitative Evaluation Suite**: Automated benchmarks tracking Hit Rate@3, MRR, Precision, and Faithfulness.

---

## 📊 Benchmark Evaluation Results

Evaluated against the standardized benchmark dataset (`docs/eval_benchmark_dataset.json`):

| Metric | Measured Score | Evaluation Target | Description |
| :--- | :---: | :---: | :--- |
| **Hit Rate@3** | **100.0%** | $\ge 90\%$ | Expected context retrieved within top-3 candidates |
| **Mean Recip. Rank (MRR)** | **1.0000** | $\ge 0.85$ | Average reciprocal rank of first relevant chunk |
| **Precision@3** | **41.7%** | $\ge 35\%$ | Evidence keyword precision across top retrieved chunks |
| **Faithfulness** | **0.50 - 1.00** | $\ge 0.75$ | Contextual grounding ratio on answering claims |
| **p50 Latency (Warm)** | **69.8 ms** | $< 150\text{ ms}$ | Steady-state retrieval and reranking latency |

Detailed results saved to [`docs/eval_results.json`](file:///docs/eval_results.json).

---

## 🚀 Quickstart

### 1. Local Environment Setup

```bash
# Backend Setup
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Unix: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend Setup
cd ../frontend
npm install
npm run dev
```

Visit **http://localhost:3000** for the UI and **http://localhost:8000/docs** for the OpenAPI specification.

### 2. Docker Compose (Production Deployment)

```bash
docker-compose up --build -d
```

---

## 🧪 Testing & Quality Gates

Run the automated test suite:

```bash
cd backend
python -m pytest tests/ -v
```

Run the standalone evaluation benchmark:

```bash
cd backend
python -m app.eval.benchmark
```

---

## 📚 Technical Documentation

- [Architecture Specification](docs/ARCHITECTURE.md)
- [Security & Threat Model](docs/SECURITY.md)
- [Quantitative Evaluation Framework](docs/EVALUATION.md)
- [Production Deployment Guide](docs/DEPLOYMENT.md)
- [Operations & SRE Runbook](docs/OPERATIONS.md)
- [Production Audit Report](docs/PRODUCTION_AUDIT.md)
