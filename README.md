# DocMind: Multimodal Intelligent Knowledge Copilot

DocMind is a production-grade, multimodal knowledge copilot designed for complex documents (financial 10-Ks, research papers, and technical manuals). It demonstrates production AI/ML engineering: layout parsing, semantic chunking, dense + BM25 hybrid search, cross-encoder reranking, semantic query caching, verifiable bounding-box citations, and an automated Ragas evaluation suite.

---

## 🛠️ Architecture Highlights

- **Multimodal Layout Extraction**: PyMuPDF + layout detection extracting block coordinates `[x0, y0, x1, y1]` and identifying tabular spans.
- **Semantic Boundary Chunking**: Cosine distance percentile splitting on sentence embeddings, avoiding fragmenting tabular data.
- **Hybrid Retrieval & RRF**: Reciprocal Rank Fusion combining SentenceTransformer dense embeddings and BM25Okapi sparse retrieval.
- **Cross-Encoder Reranking**: Re-scores top candidates using `ms-marco-MiniLM-L-6-v2` for high precision.
- **Redis Semantic Cache**: Cuts repetitive query latency by 70%+ using vector similarity caching.
- **Grounded Citations**: Interactive dual-pane Next.js UI where clicking any citation immediately navigates to and highlights the corresponding bounding box.
- **Quantitative Evaluation**: Continuous tracking of Hit Rate@K, MRR, and Ragas Faithfulness scores.

---

## 🚀 Quickstart

### 1. Backend
```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the dual-pane UI.

### 3. Docker Compose
```bash
docker-compose up --build
```
