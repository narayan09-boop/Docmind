/**
 * DocMind Centralized Typed API Client
 * Interfaces with FastAPI backend with error handling, tenant isolation, and streaming support.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Citation {
  citation_id: number;
  filename: string;
  page: number;
  bboxes: number[][];
  snippet: string;
  rerank_score: number;
}

export interface QueryResponse {
  query: string;
  answer: string;
  is_cached: boolean;
  similarity_score?: number;
  latency_ms: number;
  citations: Citation[];
  tenant_id: string;
}

export interface IngestionResponse {
  status: string;
  filename: string;
  doc_hash: string;
  tenant_id: string;
  elements_extracted: number;
  chunks_generated: number;
  new_chunks_indexed: number;
  indexing_latency_ms: number;
}

export interface SystemStats {
  tenant_id: string;
  indexed_chunks: number;
  cached_queries: number;
  embedding_model: string;
  reranker_model: string;
  status: string;
}

export interface EvalResultItem {
  id: string;
  query: string;
  latency_ms: number;
  retrieved_count: number;
  top_doc?: string;
  expected_doc?: string;
  faithfulness: number;
}

export interface BenchmarkSummary {
  dataset_name: string;
  dataset_version: string;
  total_examples: number;
  hit_rate_at_3: number;
  mrr: number;
  precision_at_3: number;
  average_faithfulness: number;
  latency_p50_ms: number;
  latency_p95_ms: number;
  timestamp: number;
  example_results: EvalResultItem[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMsg = `HTTP Error ${res.status}`;
    try {
      const errData = await res.json();
      errMsg = errData.detail || errData.message || errMsg;
    } catch {
      // Body not JSON
    }
    throw new ApiError(res.status, errMsg);
  }
  return res.json();
}

export const api = {
  async getHealth() {
    const res = await fetch(`${API_BASE_URL}/health/live`);
    return handleResponse<{ status: string; service: string }>(res);
  },

  async getStats(tenantId: string = "default"): Promise<SystemStats> {
    const res = await fetch(`${API_BASE_URL}/api/v1/stats`, {
      headers: { "X-Tenant-ID": tenantId }
    });
    return handleResponse<SystemStats>(res);
  },

  async ingestDocument(file: File, tenantId: string = "default"): Promise<IngestionResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE_URL}/api/v1/ingest`, {
      method: "POST",
      headers: { "X-Tenant-ID": tenantId },
      body: formData,
    });
    return handleResponse<IngestionResponse>(res);
  },

  async query(
    queryText: string, 
    topK: number = 5, 
    rerankTopK: number = 3, 
    tenantId: string = "default"
  ): Promise<QueryResponse> {
    const res = await fetch(`${API_BASE_URL}/api/v1/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-ID": tenantId,
      },
      body: JSON.stringify({
        query: queryText,
        top_k: topK,
        rerank_top_k: rerankTopK
      }),
    });
    return handleResponse<QueryResponse>(res);
  },

  async runBenchmark(tenantId: string = "default"): Promise<BenchmarkSummary> {
    const res = await fetch(`${API_BASE_URL}/api/v1/eval/benchmark`, {
      headers: { "X-Tenant-ID": tenantId }
    });
    return handleResponse<BenchmarkSummary>(res);
  },

  async getConfig(tenantId: string = "default"): Promise<Record<string, any>> {
    const res = await fetch(`${API_BASE_URL}/api/v1/config`, {
      headers: { "X-Tenant-ID": tenantId }
    });
    return handleResponse<Record<string, any>>(res);
  },

  async getDocuments(tenantId: string = "default"): Promise<Array<{ filename: string; doc_hash: string; chunk_count: number; created_at: number }>> {
    const res = await fetch(`${API_BASE_URL}/api/v1/documents`, {
      headers: { "X-Tenant-ID": tenantId }
    });
    return handleResponse<Array<{ filename: string; doc_hash: string; chunk_count: number; created_at: number }>>(res);
  }
};
