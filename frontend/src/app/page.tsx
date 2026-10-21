"use client";

import React, { useState, useEffect } from "react";
import { 
  FileText, Upload, Sparkles, Database, CheckCircle2, 
  BarChart3, RefreshCw, Send, ShieldAlert, Cpu, Layers, Bookmark,
  ChevronRight, Search, Eye, ExternalLink, Copy, Check, Activity, 
  Settings, Sliders, AlertCircle, ArrowUpRight, Clock, HelpCircle,
  FileCode, Terminal, Compass, Download, ShieldCheck
} from "lucide-react";
import { api, SystemStats, BenchmarkSummary, Citation, IngestionResponse } from "../lib/api";

type ActiveTab = "observatory" | "ingestion" | "retrieval" | "generation" | "evaluation" | "configuration";

interface ActivityEvent {
  id: string;
  type: "info" | "success" | "warn";
  message: string;
  timestamp: string;
}

export default function DocMindResearchPlatform() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("observatory");
  const [tenantId, setTenantId] = useState<string>("default");
  
  // Real System State
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [systemConfig, setSystemConfig] = useState<Record<string, any> | null>(null);
  const [isLive, setIsLive] = useState<boolean | null>(null);
  const [statsLoading, setStatsLoading] = useState<boolean>(true);
  const [activityEvents, setActivityEvents] = useState<ActivityEvent[]>([]);

  // Ingestion State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isIngesting, setIsIngesting] = useState<boolean>(false);
  const [ingestResult, setIngestResult] = useState<IngestionResponse | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const [documentsHistory, setDocumentsHistory] = useState<Array<{ filename: string; doc_hash: string; chunk_count: number; created_at: number }>>([]);

  // Retrieval Playground State
  const [retrievalQuery, setRetrievalQuery] = useState<string>("");
  const [topK, setTopK] = useState<number>(5);
  const [rerankTopK, setRerankTopK] = useState<number>(3);
  const [retrievedCitations, setRetrievedCitations] = useState<Citation[]>([]);
  const [retrievalLatency, setRetrievalLatency] = useState<number | null>(null);
  const [isRetrieving, setIsRetrieving] = useState<boolean>(false);
  const [retrievalError, setRetrievalError] = useState<string | null>(null);

  // Generation Playground State
  const [generationQuery, setGenerationQuery] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationAnswer, setGenerationAnswer] = useState<string | null>(null);
  const [generationCitations, setGenerationCitations] = useState<Citation[]>([]);
  const [generationLatency, setGenerationLatency] = useState<number | null>(null);
  const [isCachedHit, setIsCachedHit] = useState<boolean>(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  // Evaluation Laboratory State
  const [benchmarkData, setBenchmarkData] = useState<BenchmarkSummary | null>(null);
  const [isBenchmarking, setIsBenchmarking] = useState<boolean>(false);
  const [benchmarkError, setBenchmarkError] = useState<string | null>(null);

  // Copied indicator
  const [copied, setCopied] = useState<boolean>(false);

  // Helper to log dynamic events
  const addEvent = (message: string, type: "info" | "success" | "warn" = "info") => {
    const timeStr = new Date().toLocaleTimeString();
    setActivityEvents(prev => [
      { id: `${Date.now()}-${Math.random()}`, type, message, timestamp: timeStr },
      ...prev.slice(0, 19)
    ]);
  };

  // Fetch real data on mount & tenant switch
  useEffect(() => {
    fetchInitialData();
  }, [tenantId]);

  const fetchInitialData = async () => {
    setStatsLoading(true);
    try {
      const [healthRes, statsRes, docsRes, configRes] = await Promise.allSettled([
        api.getHealth(),
        api.getStats(tenantId),
        api.getDocuments(tenantId),
        api.getConfig(tenantId)
      ]);

      if (healthRes.status === "fulfilled") {
        setIsLive(true);
        addEvent(`Connected to FastAPI backend (${healthRes.value.service})`, "success");
      } else {
        setIsLive(false);
        addEvent("Backend connection offline at http://localhost:8000", "warn");
      }

      if (statsRes.status === "fulfilled") {
        setSystemStats(statsRes.value);
      }

      if (docsRes.status === "fulfilled") {
        setDocumentsHistory(docsRes.value);
      }

      if (configRes.status === "fulfilled") {
        setSystemConfig(configRes.value);
      }
    } catch {
      setIsLive(false);
    } finally {
      setStatsLoading(false);
    }
  };

  // Run Real Ingestion
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.[0]) return;
    const file = e.target.files[0];
    setSelectedFile(file);
    setIsIngesting(true);
    setIngestError(null);
    setIngestResult(null);

    try {
      const res = await api.ingestDocument(file, tenantId);
      setIngestResult(res);
      addEvent(`Document '${res.filename}' parsed and indexed (${res.new_chunks_indexed} chunks, ${res.indexing_latency_ms}ms)`, "success");
      
      // Refresh documents and stats from backend
      const [docs, stats] = await Promise.all([
        api.getDocuments(tenantId),
        api.getStats(tenantId)
      ]);
      setDocumentsHistory(docs);
      setSystemStats(stats);
    } catch (err: any) {
      setIngestError(err.message || "Failed to parse document");
      addEvent(`Ingestion failure for '${file.name}': ${err.message}`, "warn");
    } finally {
      setIsIngesting(false);
    }
  };

  // Run Real Retrieval Query
  const executeRetrieval = async () => {
    if (!retrievalQuery.trim() || isRetrieving) return;
    setIsRetrieving(true);
    setRetrievalError(null);

    try {
      const res = await api.query(retrievalQuery, topK, rerankTopK, tenantId);
      setRetrievedCitations(res.citations);
      setRetrievalLatency(res.latency_ms);
      addEvent(`Retrieval query executed (${res.citations.length} candidates in ${res.latency_ms}ms)`, "info");
    } catch (err: any) {
      setRetrievalError(err.message || "Retrieval request failed");
      setRetrievedCitations([]);
      addEvent(`Retrieval error: ${err.message}`, "warn");
    } finally {
      setIsRetrieving(false);
    }
  };

  // Run Real Grounded Generation Query
  const executeGeneration = async () => {
    if (!generationQuery.trim() || isGenerating) return;
    setIsGenerating(true);
    setGenerationError(null);
    setGenerationAnswer(null);

    try {
      const res = await api.query(generationQuery, topK, rerankTopK, tenantId);
      setGenerationAnswer(res.answer);
      setGenerationCitations(res.citations);
      setGenerationLatency(res.latency_ms);
      setIsCachedHit(res.is_cached);
      addEvent(`Inference completed in ${res.latency_ms}ms (cache hit: ${res.is_cached})`, "info");
    } catch (err: any) {
      setGenerationError(err.message || "Inference request failed");
      addEvent(`Inference error: ${err.message}`, "warn");
    } finally {
      setIsGenerating(false);
    }
  };

  // Run Real Evaluation Benchmark
  const executeBenchmark = async () => {
    if (isBenchmarking) return;
    setIsBenchmarking(true);
    setBenchmarkError(null);

    try {
      const res = await api.runBenchmark(tenantId);
      setBenchmarkData(res);
      addEvent(`Evaluation benchmark completed: Hit Rate@3 = ${(res.hit_rate_at_3 * 100).toFixed(1)}%, MRR = ${res.mrr.toFixed(4)}`, "success");
    } catch (err: any) {
      setBenchmarkError(err.message || "Benchmark failed to complete on server");
      addEvent(`Benchmark error: ${err.message}`, "warn");
    } finally {
      setIsBenchmarking(false);
    }
  };

  const handleCopyAnswer = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex h-screen bg-paper text-espresso font-sans overflow-hidden">
      {/* LEFT NAVIGATION COLUMN */}
      <aside className="w-64 hairline-r bg-sand/60 flex flex-col justify-between shrink-0 select-none">
        <div>
          {/* Platform Identity */}
          <div className="p-5 hairline-b">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-pixel text-[9px] text-terracotta bg-terracotta/10 px-1.5 py-0.5 border border-terracotta/20">
                LAB / 01
              </span>
              <span className="font-mono text-[11px] text-muted tracking-tight">v1.1.0</span>
            </div>
            <h1 className="font-serif text-2xl font-bold tracking-tight text-espresso leading-none">
              DocMind
            </h1>
            <p className="text-[12px] text-muted mt-1 font-serif italic">
              Multimodal RAG Research Console
            </p>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            <button
              onClick={() => setActiveTab("observatory")}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-sm transition-colors text-left ${
                activeTab === "observatory" 
                  ? "bg-surface text-espresso shadow-sm border border-taupe font-semibold" 
                  : "text-muted hover:text-espresso hover:bg-sand/80"
              }`}
            >
              <span className="flex items-center gap-2.5">
                <Compass className="w-4 h-4 text-terracotta" />
                <span>Observatory</span>
              </span>
              <span className="font-pixel text-[8px] text-muted/60">01</span>
            </button>

            <button
              onClick={() => setActiveTab("ingestion")}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-sm transition-colors text-left ${
                activeTab === "ingestion" 
                  ? "bg-surface text-espresso shadow-sm border border-taupe font-semibold" 
                  : "text-muted hover:text-espresso hover:bg-sand/80"
              }`}
            >
              <span className="flex items-center gap-2.5">
                <Upload className="w-4 h-4 text-sage" />
                <span>Ingestion Workspace</span>
              </span>
              <span className="font-pixel text-[8px] text-muted/60">02</span>
            </button>

            <button
              onClick={() => setActiveTab("retrieval")}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-sm transition-colors text-left ${
                activeTab === "retrieval" 
                  ? "bg-surface text-espresso shadow-sm border border-taupe font-semibold" 
                  : "text-muted hover:text-espresso hover:bg-sand/80"
              }`}
            >
              <span className="flex items-center gap-2.5">
                <Layers className="w-4 h-4 text-espresso" />
                <span>Retrieval Playground</span>
              </span>
              <span className="font-pixel text-[8px] text-muted/60">03</span>
            </button>

            <button
              onClick={() => setActiveTab("generation")}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-sm transition-colors text-left ${
                activeTab === "generation" 
                  ? "bg-surface text-espresso shadow-sm border border-taupe font-semibold" 
                  : "text-muted hover:text-espresso hover:bg-sand/80"
              }`}
            >
              <span className="flex items-center gap-2.5">
                <Sparkles className="w-4 h-4 text-terracotta" />
                <span>Grounded Inference</span>
              </span>
              <span className="font-pixel text-[8px] text-muted/60">04</span>
            </button>

            <button
              onClick={() => setActiveTab("evaluation")}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-sm transition-colors text-left ${
                activeTab === "evaluation" 
                  ? "bg-surface text-espresso shadow-sm border border-taupe font-semibold" 
                  : "text-muted hover:text-espresso hover:bg-sand/80"
              }`}
            >
              <span className="flex items-center gap-2.5">
                <BarChart3 className="w-4 h-4 text-forest" />
                <span>Evaluation Laboratory</span>
              </span>
              <span className="font-pixel text-[8px] text-muted/60">05</span>
            </button>

            <button
              onClick={() => setActiveTab("configuration")}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-sm transition-colors text-left ${
                activeTab === "configuration" 
                  ? "bg-surface text-espresso shadow-sm border border-taupe font-semibold" 
                  : "text-muted hover:text-espresso hover:bg-sand/80"
              }`}
            >
              <span className="flex items-center gap-2.5">
                <Sliders className="w-4 h-4 text-muted" />
                <span>Configuration Studio</span>
              </span>
              <span className="font-pixel text-[8px] text-muted/60">06</span>
            </button>
          </nav>
        </div>

        {/* System Heartbeat & Tenant Status */}
        <div className="p-4 hairline-t bg-sand/30 space-y-2">
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-muted">HOST:</span>
            <span className="flex items-center gap-1.5 font-medium">
              <span className={`w-2 h-2 rounded-full ${isLive ? "bg-forest" : "bg-brick"}`} />
              {isLive ? "FASTAPI : 8000" : "OFFLINE"}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-muted">TENANT:</span>
            <input 
              type="text" 
              value={tenantId}
              onChange={(e) => setTenantId(e.target.value)}
              className="w-20 bg-surface border border-taupe px-1.5 py-0.5 text-[10px] text-right font-mono focus:outline-none"
              title="Set X-Tenant-ID header"
            />
          </div>
        </div>
      </aside>

      {/* MAIN VIEWPORT */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Editorial Breadcrumb Bar */}
        <header className="h-14 hairline-b bg-surface px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <span className="font-pixel text-[9px] text-muted uppercase">SECTION</span>
            <ChevronRight className="w-3.5 h-3.5 text-taupe-dark" />
            <span className="font-serif text-sm font-semibold tracking-wide capitalize text-espresso">
              {activeTab}
            </span>
            <span className="text-muted/40 font-mono text-xs">/</span>
            <span className="font-mono text-xs text-muted">
              {activeTab === "evaluation" ? "BENCHMARK_SUITE_v1" : "LIVE_TELEMETRY"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="font-mono text-xs px-2.5 py-1 bg-sand/60 border border-taupe rounded-sm text-espresso-light flex items-center gap-2">
              <span className="text-muted">CACHE:</span>
              <span className="font-semibold text-espresso">{systemStats?.cached_queries ?? 0}</span>
              <span className="text-muted">| CHUNKS:</span>
              <span className="font-semibold text-terracotta">{systemStats?.indexed_chunks ?? 0}</span>
            </div>
            <button 
              onClick={fetchInitialData}
              className="p-1.5 border border-taupe hover:bg-sand/60 rounded-sm text-muted hover:text-espresso transition-colors"
              title="Refresh telemetry"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${statsLoading ? "animate-spin" : ""}`} />
            </button>
          </div>
        </header>

        {/* Dynamic Workspace Container */}
        <main className="flex-1 overflow-y-auto p-8">
          {/* TAB 1: OBSERVATORY */}
          {activeTab === "observatory" && (
            <div className="max-w-5xl mx-auto space-y-8">
              {/* Editorial Title Banner */}
              <div className="border-b border-taupe pb-4">
                <span className="font-pixel text-[9px] text-terracotta">SYS_METRICS / 001</span>
                <h2 className="font-serif text-3xl font-bold tracking-tight text-espresso mt-1">
                  System Observatory
                </h2>
                <p className="text-xs text-muted font-serif italic mt-0.5">
                  Live backend diagnostics, model registry parameters, and data partition telemetry.
                </p>
              </div>

              {/* Editorial Metric Grid */}
              <div className="grid grid-cols-4 gap-4">
                <div className="paper-surface p-4">
                  <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">Indexed Chunks</span>
                  <div className="font-serif text-3xl font-bold text-espresso mt-1">
                    {systemStats?.indexed_chunks ?? 0}
                  </div>
                  <span className="text-[11px] text-muted font-serif italic mt-1 block">Active across tenant '{tenantId}'</span>
                </div>

                <div className="paper-surface p-4">
                  <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">Embedding Model</span>
                  <div className="font-serif text-xl font-bold text-terracotta mt-1 truncate" title={systemStats?.embedding_model}>
                    {systemStats?.embedding_model || "Loading..."}
                  </div>
                  <span className="text-[11px] text-muted font-serif italic mt-1 block">
                    {systemConfig?.EMBEDDING_DIMENSION ? `${systemConfig.EMBEDDING_DIMENSION} dimensions` : "SentenceTransformers"}
                  </span>
                </div>

                <div className="paper-surface p-4">
                  <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">Reranker Model</span>
                  <div className="font-serif text-xl font-bold text-sage-dark mt-1 truncate" title={systemStats?.reranker_model}>
                    {systemStats?.reranker_model || "Loading..."}
                  </div>
                  <span className="text-[11px] text-muted font-serif italic mt-1 block">CrossEncoder verification</span>
                </div>

                <div className="paper-surface p-4">
                  <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">Semantic Cache</span>
                  <div className="font-serif text-3xl font-bold text-forest mt-1">
                    {systemStats?.cached_queries ?? 0}
                  </div>
                  <span className="text-[11px] text-muted font-serif italic mt-1 block">
                    {systemConfig ? `Threshold \u2265 ${systemConfig.SEMANTIC_CACHE_THRESHOLD} sim` : "Active partition"}
                  </span>
                </div>
              </div>

              {/* Technical Architecture Overview */}
              <div className="paper-surface p-6">
                <div className="flex items-center justify-between pb-3 hairline-b mb-4">
                  <h3 className="font-serif text-lg font-bold text-espresso">
                    Verified Pipeline Stages
                  </h3>
                  <span className="font-pixel text-[8px] text-forest bg-forest/10 px-2 py-0.5 border border-forest/20">
                    {isLive ? "OPERATIONAL" : "OFFLINE"}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-6 text-xs leading-relaxed">
                  <div>
                    <h4 className="font-mono text-[11px] font-semibold text-terracotta uppercase mb-1">
                      01. Layout & Chunking
                    </h4>
                    <p className="text-muted">
                      PyMuPDF parses layout coordinates <code>[x0, y0, x1, y1]</code>. Cosine distance drops segment semantic sentences while preserving tabular continuity. Content is SHA-256 hashed for idempotent indexing.
                    </p>
                  </div>
                  <div>
                    <h4 className="font-mono text-[11px] font-semibold text-espresso uppercase mb-1">
                      02. Hybrid Search & RRF
                    </h4>
                    <p className="text-muted">
                      Combines dense embeddings with BM25Okapi inverted index using Reciprocal Rank Fusion (smoothing constant <code>k=60</code>), eliminating scale divergence between sparse and dense scores.
                    </p>
                  </div>
                  <div>
                    <h4 className="font-mono text-[11px] font-semibold text-sage-dark uppercase mb-1">
                      03. Grounding & Guardrails
                    </h4>
                    <p className="text-muted">
                      Retrieved contexts are fenced in structural XML tags to mitigate indirect prompt injection. Verified citation links map directly back to source document pages and layout coordinates.
                    </p>
                  </div>
                </div>
              </div>

              {/* Dynamic Activity Timeline */}
              <div className="paper-surface p-5 space-y-3">
                <div className="flex items-center justify-between hairline-b pb-2">
                  <span className="font-serif text-sm font-semibold text-espresso">System Event Journal</span>
                  <span className="font-mono text-[10px] text-muted">
                    {activityEvents.length} RECORDED EVENTS
                  </span>
                </div>
                {activityEvents.length === 0 ? (
                  <p className="text-xs font-serif italic text-muted py-2">
                    Awaiting pipeline events. Perform an ingestion, search, or evaluation to log activity.
                  </p>
                ) : (
                  <div className="space-y-2 text-xs font-mono">
                    {activityEvents.map((evt) => (
                      <div key={evt.id} className="flex items-center justify-between py-1.5 hairline-b border-taupe/40 text-muted">
                        <span className="flex items-center gap-2">
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            evt.type === "success" ? "bg-forest" : evt.type === "warn" ? "bg-ochre" : "bg-terracotta"
                          }`} />
                          <span className="text-espresso">{evt.message}</span>
                        </span>
                        <span>{evt.timestamp}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: INGESTION WORKSPACE */}
          {activeTab === "ingestion" && (
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="border-b border-taupe pb-4">
                <span className="font-pixel text-[9px] text-sage-dark">INGEST / 002</span>
                <h2 className="font-serif text-3xl font-bold tracking-tight text-espresso mt-1">
                  Document Ingestion Workspace
                </h2>
                <p className="text-xs text-muted font-serif italic mt-0.5">
                  Multi-stage parsing, layout extraction, tabular bounding-box anchors, and idempotent chunk generation.
                </p>
              </div>

              {/* Pipeline Stage Indicator */}
              <div className="paper-panel p-3.5 flex items-center justify-between font-mono text-[11px] text-muted">
                <div className="flex items-center gap-1.5 text-espresso font-semibold">
                  <span className="font-pixel text-[8px] text-terracotta">01</span> RECEIVED
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-taupe-dark" />
                <div className="flex items-center gap-1.5 text-espresso font-semibold">
                  <span className="font-pixel text-[8px] text-terracotta">02</span> PARSED
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-taupe-dark" />
                <div className="flex items-center gap-1.5 text-espresso font-semibold">
                  <span className="font-pixel text-[8px] text-terracotta">03</span> CHUNKED
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-taupe-dark" />
                <div className="flex items-center gap-1.5 text-espresso font-semibold">
                  <span className="font-pixel text-[8px] text-terracotta">04</span> EMBEDDED
                </div>
                <ChevronRight className="w-3.5 h-3.5 text-taupe-dark" />
                <div className="flex items-center gap-1.5 text-forest font-semibold">
                  <span className="font-pixel text-[8px] text-forest">05</span> INDEXED
                </div>
              </div>

              {/* Upload Card */}
              <div className="paper-surface p-8 text-center border-dashed border-2 border-taupe-dark/60 hover:border-terracotta transition-colors">
                <FileText className="w-8 h-8 text-terracotta mx-auto mb-2 opacity-80" />
                <h3 className="font-serif text-base font-bold text-espresso">
                  Select a research paper, Form 10-Q, or financial PDF
                </h3>
                <p className="text-xs text-muted mt-1 font-serif italic">
                  Maximum file size: {systemConfig ? `${(systemConfig.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)).toFixed(0)} MB` : "15 MB"}. Enforces %PDF magic byte signature.
                </p>
                <div className="mt-4">
                  <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 bg-espresso hover:bg-espresso-dark text-paper text-xs font-mono font-medium rounded-sm transition-colors shadow-sm">
                    <Upload className="w-3.5 h-3.5 text-terracotta-light" />
                    <span>{isIngesting ? "Parsing & Indexing..." : "Browse Local File"}</span>
                    <input 
                      type="file" 
                      accept=".pdf" 
                      onChange={handleFileUpload}
                      disabled={isIngesting}
                      className="hidden" 
                    />
                  </label>
                </div>
              </div>

              {/* Ingestion Error Alert */}
              {ingestError && (
                <div className="p-3.5 bg-brick/10 border border-brick/30 text-brick text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>Ingestion Error: {ingestError}</span>
                </div>
              )}

              {/* Ingestion Success Details */}
              {ingestResult && (
                <div className="paper-surface p-5 space-y-3 border-l-4 border-l-forest">
                  <div className="flex items-center justify-between">
                    <span className="font-serif text-sm font-bold text-forest">
                      Document Successfully Indexed
                    </span>
                    <span className="font-mono text-xs text-muted">
                      Latency: <strong>{ingestResult.indexing_latency_ms} ms</strong>
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-3 text-xs font-mono">
                    <div className="p-2 bg-sand/40 border border-taupe">
                      <span className="text-[10px] text-muted uppercase block">Document</span>
                      <span className="font-semibold text-espresso truncate block">{ingestResult.filename}</span>
                    </div>
                    <div className="p-2 bg-sand/40 border border-taupe">
                      <span className="text-[10px] text-muted uppercase block">Content Hash</span>
                      <span className="font-semibold text-espresso truncate block">{ingestResult.doc_hash}</span>
                    </div>
                    <div className="p-2 bg-sand/40 border border-taupe">
                      <span className="text-[10px] text-muted uppercase block">Elements</span>
                      <span className="font-semibold text-espresso">{ingestResult.elements_extracted}</span>
                    </div>
                    <div className="p-2 bg-sand/40 border border-taupe">
                      <span className="text-[10px] text-muted uppercase block">New Chunks</span>
                      <span className="font-semibold text-terracotta">{ingestResult.new_chunks_indexed}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Document Registry Table (Real Backend Documents) */}
              <div className="paper-surface overflow-hidden">
                <div className="p-3 hairline-b bg-sand/40 flex items-center justify-between">
                  <span className="font-serif text-xs font-bold text-espresso uppercase tracking-wider">
                    Document Registry (Tenant: {tenantId})
                  </span>
                  <span className="font-mono text-[10px] text-muted">TOTAL: {documentsHistory.length}</span>
                </div>
                {documentsHistory.length === 0 ? (
                  <div className="p-8 text-center text-xs font-serif italic text-muted">
                    No documents indexed for tenant '{tenantId}' yet. Upload a PDF file above to begin ingestion.
                  </div>
                ) : (
                  <table className="w-full text-left text-xs">
                    <thead className="bg-sand/30 font-mono text-[10px] text-muted uppercase hairline-b">
                      <tr>
                        <th className="p-3">File Name</th>
                        <th className="p-3">Content Hash</th>
                        <th className="p-3">Chunks</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Created</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-taupe/40 font-mono text-xs">
                      {documentsHistory.map((d, i) => (
                        <tr key={i} className="hover:bg-sand/20">
                          <td className="p-3 font-medium text-espresso flex items-center gap-2">
                            <FileText className="w-3.5 h-3.5 text-terracotta" />
                            <span>{d.filename}</span>
                          </td>
                          <td className="p-3 text-muted">{d.doc_hash}</td>
                          <td className="p-3 text-espresso font-semibold">{d.chunk_count}</td>
                          <td className="p-3">
                            <span className="px-1.5 py-0.5 rounded-sm bg-forest/10 text-forest border border-forest/20 text-[10px]">
                              INDEXED
                            </span>
                          </td>
                          <td className="p-3 text-muted">{new Date(d.created_at * 1000).toLocaleTimeString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: RETRIEVAL PLAYGROUND */}
          {activeTab === "retrieval" && (
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="border-b border-taupe pb-4">
                <span className="font-pixel text-[9px] text-terracotta">SEARCH / 003</span>
                <h2 className="font-serif text-3xl font-bold tracking-tight text-espresso mt-1">
                  Retrieval Playground
                </h2>
                <p className="text-xs text-muted font-serif italic mt-0.5">
                  Inspect dense vector embeddings, sparse BM25 scoring, RRF rank fusion, and Cross-Encoder score distributions.
                </p>
              </div>

              {/* Query & Parameter Console */}
              <div className="paper-surface p-5 space-y-4">
                <div className="space-y-1.5">
                  <label className="font-serif text-xs font-semibold text-espresso flex items-center justify-between">
                    <span>Query Expression</span>
                    <span className="font-mono text-[10px] text-muted">TARGET: HYBRID DENSE + BM25</span>
                  </label>
                  <div className="flex gap-2">
                    <input 
                      type="text" 
                      value={retrievalQuery}
                      onChange={(e) => setRetrievalQuery(e.target.value)}
                      placeholder="Enter search expression or question to retrieve evidence..."
                      className="flex-1 bg-surface border border-taupe px-3 py-2 text-xs font-mono text-espresso focus:outline-none focus:border-terracotta"
                    />
                    <button
                      onClick={executeRetrieval}
                      disabled={isRetrieving || !retrievalQuery.trim()}
                      className="px-4 py-2 bg-espresso hover:bg-espresso-dark disabled:opacity-40 text-paper text-xs font-mono font-medium rounded-sm transition-colors flex items-center gap-2"
                    >
                      <Search className="w-3.5 h-3.5 text-terracotta-light" />
                      <span>{isRetrieving ? "Searching..." : "Execute Search"}</span>
                    </button>
                  </div>
                </div>

                {/* Tunable Parameters */}
                <div className="grid grid-cols-3 gap-4 pt-2 hairline-t text-xs font-mono">
                  <div>
                    <label className="text-[10px] text-muted block mb-1 uppercase">Top-K Candidates: {topK}</label>
                    <input 
                      type="range" 
                      min="1" 
                      max="15" 
                      value={topK}
                      onChange={(e) => setTopK(Number(e.target.value))}
                      className="w-full accent-terracotta cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted block mb-1 uppercase">Rerank Top-K: {rerankTopK}</label>
                    <input 
                      type="range" 
                      min="1" 
                      max="10" 
                      value={rerankTopK}
                      onChange={(e) => setRerankTopK(Number(e.target.value))}
                      className="w-full accent-terracotta cursor-pointer"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted block mb-1 uppercase">RRF Fusion Constant</label>
                    <span className="font-semibold text-espresso">k = {systemConfig?.RRF_K ?? 60}</span>
                  </div>
                </div>
              </div>

              {/* Retrieval Status & Latency */}
              {retrievalLatency !== null && (
                <div className="flex items-center justify-between text-xs font-mono text-muted px-1">
                  <span>Found <strong>{retrievedCitations.length}</strong> ranked candidates</span>
                  <span>Execution Latency: <strong className="text-espresso">{retrievalLatency} ms</strong></span>
                </div>
              )}

              {retrievalError && (
                <div className="p-3 bg-brick/10 border border-brick/30 text-brick text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{retrievalError}</span>
                </div>
              )}

              {/* Retrieved Evidence Results */}
              <div className="space-y-3">
                {retrievedCitations.length === 0 && !isRetrieving ? (
                  <div className="paper-panel p-8 text-center text-xs font-serif italic text-muted">
                    No active retrieval results. Enter a query above to inspect ranked evidence chunks from indexed documents.
                  </div>
                ) : (
                  retrievedCitations.map((c) => (
                    <div key={c.citation_id} className="paper-surface p-4 space-y-2">
                      <div className="flex items-center justify-between hairline-b pb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-pixel text-[9px] bg-terracotta text-paper px-1.5 py-0.5">
                            RANK #{c.citation_id}
                          </span>
                          <span className="font-mono text-xs font-semibold text-espresso">
                            {c.filename}
                          </span>
                          <span className="font-mono text-[11px] text-muted">
                            (Page {c.page})
                          </span>
                        </div>
                        <div className="font-mono text-[11px] text-muted">
                          Reranker Score: <strong className="text-espresso">{c.rerank_score}</strong>
                        </div>
                      </div>
                      <p className="text-xs leading-relaxed text-espresso font-serif italic">
                        "{c.snippet}"
                      </p>
                      {c.bboxes.length > 0 && (
                        <div className="text-[10px] font-mono text-muted pt-1 flex items-center gap-1">
                          <Eye className="w-3 h-3 text-terracotta" />
                          <span>Layout Bounding Box: [{c.bboxes[0].join(", ")}]</span>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 4: GROUNDED INFERENCE */}
          {activeTab === "generation" && (
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="border-b border-taupe pb-4">
                <span className="font-pixel text-[9px] text-sage-dark">GEN / 004</span>
                <h2 className="font-serif text-3xl font-bold tracking-tight text-espresso mt-1">
                  Grounded Inference Engine
                </h2>
                <p className="text-xs text-muted font-serif italic mt-0.5">
                  Full RAG pipeline testing: prompt injection isolation, verifiable in-text citation grounding, and latency profiling.
                </p>
              </div>

              {/* Query Form */}
              <div className="paper-surface p-5 space-y-3">
                <label className="font-serif text-xs font-semibold text-espresso block">
                  Question for Grounded Synthesis
                </label>
                <div className="flex gap-2">
                  <input 
                    type="text"
                    value={generationQuery}
                    onChange={(e) => setGenerationQuery(e.target.value)}
                    placeholder="Ask a question based on indexed documents..."
                    className="flex-1 bg-surface border border-taupe px-3 py-2 text-xs font-mono text-espresso focus:outline-none focus:border-terracotta"
                  />
                  <button
                    onClick={executeGeneration}
                    disabled={isGenerating || !generationQuery.trim()}
                    className="px-5 py-2 bg-espresso hover:bg-espresso-dark disabled:opacity-40 text-paper text-xs font-mono font-medium rounded-sm transition-colors flex items-center gap-2"
                  >
                    <Send className="w-3.5 h-3.5 text-terracotta-light" />
                    <span>{isGenerating ? "Synthesizing..." : "Generate Grounded Answer"}</span>
                  </button>
                </div>
              </div>

              {/* Telemetry Strip */}
              {generationLatency !== null && (
                <div className="flex items-center justify-between text-xs font-mono text-muted px-1">
                  <div className="flex items-center gap-3">
                    <span>Latency: <strong className="text-espresso">{generationLatency} ms</strong></span>
                    {isCachedHit && (
                      <span className="px-1.5 py-0.5 bg-forest/10 text-forest border border-forest/20 text-[10px]">
                        ⚡ SEMANTIC CACHE HIT (&ge; {systemConfig?.SEMANTIC_CACHE_THRESHOLD ?? 0.90} SIM)
                      </span>
                    )}
                  </div>
                  <span className="font-pixel text-[8px] text-muted">PROMPT_FENCED: XML</span>
                </div>
              )}

              {/* Error Message */}
              {generationError && (
                <div className="p-3 bg-brick/10 border border-brick/30 text-brick text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{generationError}</span>
                </div>
              )}

              {/* Generated Answer Display */}
              {generationAnswer && (
                <div className="paper-surface p-6 space-y-4 border-t-2 border-t-terracotta">
                  <div className="flex items-center justify-between hairline-b pb-2">
                    <span className="font-serif text-sm font-bold text-espresso">
                      Grounded Answer
                    </span>
                    <button
                      onClick={() => handleCopyAnswer(generationAnswer)}
                      className="text-xs font-mono text-muted hover:text-espresso flex items-center gap-1.5 transition-colors"
                      title="Copy response"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-forest" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? "Copied" : "Copy"}</span>
                    </button>
                  </div>

                  <p className="text-sm font-serif leading-relaxed text-espresso whitespace-pre-line">
                    {generationAnswer}
                  </p>

                  {/* Grounded Citations Provenance */}
                  {generationCitations.length > 0 && (
                    <div className="pt-3 hairline-t space-y-2">
                      <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">
                        Verified Source Citations
                      </span>
                      <div className="space-y-1.5">
                        {generationCitations.map(c => (
                          <div key={c.citation_id} className="p-2.5 bg-sand/30 border border-taupe text-xs font-mono flex items-start gap-2">
                            <span className="font-bold text-terracotta shrink-0">[Citation #{c.citation_id}]</span>
                            <div className="space-y-0.5 flex-1">
                              <span className="font-semibold text-espresso">{c.filename} — Page {c.page}</span>
                              <p className="text-muted text-[11px] font-serif italic">"{c.snippet}"</p>
                            </div>
                            <span className="text-[10px] text-muted shrink-0 font-mono">Score: {c.rerank_score}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: EVALUATION LABORATORY (SIGNATURE FEATURE) */}
          {activeTab === "evaluation" && (
            <div className="max-w-5xl mx-auto space-y-6">
              <div className="border-b border-taupe pb-4 flex items-center justify-between">
                <div>
                  <span className="font-pixel text-[9px] text-forest">EVAL_LAB / 005</span>
                  <h2 className="font-serif text-3xl font-bold tracking-tight text-espresso mt-1">
                    Evaluation Laboratory
                  </h2>
                  <p className="text-xs text-muted font-serif italic mt-0.5">
                    Continuous quantitative evaluation suite tracking Hit Rate@K, MRR, Precision, Faithfulness, and latency percentiles.
                  </p>
                </div>

                <button
                  onClick={executeBenchmark}
                  disabled={isBenchmarking}
                  className="px-4 py-2 bg-espresso hover:bg-espresso-dark disabled:opacity-40 text-paper text-xs font-mono font-medium rounded-sm transition-colors flex items-center gap-2 shadow-sm"
                >
                  <Activity className={`w-3.5 h-3.5 text-forest ${isBenchmarking ? "animate-spin" : ""}`} />
                  <span>{isBenchmarking ? "Benchmarking Suite..." : "Run Evaluation Benchmark"}</span>
                </button>
              </div>

              {/* Dataset Specification Card */}
              <div className="paper-panel p-4 flex items-center justify-between text-xs font-mono">
                <div>
                  <span className="text-muted block text-[10px] uppercase">BENCHMARK DATASET</span>
                  <span className="font-semibold text-espresso">
                    {benchmarkData?.dataset_name || "DocMind Benchmark Suite"}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[10px] uppercase">VERSION</span>
                  <span className="font-semibold text-espresso">
                    {benchmarkData?.dataset_version || "v1.0.0"}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[10px] uppercase">TEST EXAMPLES</span>
                  <span className="font-semibold text-terracotta">
                    {benchmarkData ? `${benchmarkData.total_examples} Cases` : "5 Cases"}
                  </span>
                </div>
                <div>
                  <span className="text-muted block text-[10px] uppercase">HARNESS ENGINE</span>
                  <span className="font-semibold text-espresso">RAGEvaluationHarness</span>
                </div>
              </div>

              {benchmarkError && (
                <div className="p-3 bg-brick/10 border border-brick/30 text-brick text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{benchmarkError}</span>
                </div>
              )}

              {/* Metric Cards Grid */}
              <div className="grid grid-cols-4 gap-4">
                <div className="paper-surface p-4">
                  <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">Hit Rate @ 3</span>
                  <div className="font-serif text-3xl font-bold text-forest mt-1">
                    {benchmarkData ? `${(benchmarkData.hit_rate_at_3 * 100).toFixed(1)}%` : "\u2014"}
                  </div>
                  <span className="text-[10px] text-muted font-mono mt-1 block">Expected doc in top 3</span>
                </div>

                <div className="paper-surface p-4">
                  <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">Mean Recip. Rank</span>
                  <div className="font-serif text-3xl font-bold text-espresso mt-1">
                    {benchmarkData ? benchmarkData.mrr.toFixed(4) : "\u2014"}
                  </div>
                  <span className="text-[10px] text-muted font-mono mt-1 block">MRR ranking score</span>
                </div>

                <div className="paper-surface p-4">
                  <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">Evidence Precision</span>
                  <div className="font-serif text-3xl font-bold text-terracotta mt-1">
                    {benchmarkData ? `${(benchmarkData.precision_at_3 * 100).toFixed(1)}%` : "\u2014"}
                  </div>
                  <span className="text-[10px] text-muted font-mono mt-1 block">Keyword overlap in top-k</span>
                </div>

                <div className="paper-surface p-4">
                  <span className="font-mono text-[10px] uppercase text-muted tracking-wider block">p50 Latency</span>
                  <div className="font-serif text-3xl font-bold text-sage-dark mt-1">
                    {benchmarkData ? `${benchmarkData.latency_p50_ms}` : "\u2014"}
                    {benchmarkData && <span className="text-xs font-mono font-normal text-muted"> ms</span>}
                  </div>
                  <span className="text-[10px] text-muted font-mono mt-1 block">Steady-state retrieval</span>
                </div>
              </div>

              {/* Per-Example Failure & Correctness Table */}
              <div className="paper-surface overflow-hidden">
                <div className="p-3 hairline-b bg-sand/40 flex items-center justify-between">
                  <span className="font-serif text-xs font-bold text-espresso uppercase tracking-wider">
                    Per-Example Benchmark Breakdown
                  </span>
                  <span className="font-mono text-[10px] text-muted">
                    {benchmarkData ? `EVALUATED AT: ${new Date(benchmarkData.timestamp * 1000).toLocaleTimeString()}` : "STATUS: PENDING EXECUTION"}
                  </span>
                </div>

                {!benchmarkData ? (
                  <div className="p-8 text-center text-xs font-serif italic text-muted">
                    No active evaluation run recorded. Click "Run Evaluation Benchmark" above to execute the test suite against the live retrieval engine.
                  </div>
                ) : (
                  <table className="w-full text-left text-xs">
                    <thead className="bg-sand/30 font-mono text-[10px] text-muted uppercase hairline-b">
                      <tr>
                        <th className="p-3">ID</th>
                        <th className="p-3">Query Expression</th>
                        <th className="p-3">Expected Doc</th>
                        <th className="p-3">Top Retrieved</th>
                        <th className="p-3">Faithfulness</th>
                        <th className="p-3">Latency</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-taupe/40 font-mono text-xs">
                      {benchmarkData.example_results.map((row) => (
                        <tr key={row.id} className="hover:bg-sand/20">
                          <td className="p-3 text-terracotta font-semibold">{row.id}</td>
                          <td className="p-3 font-serif italic text-espresso">{row.query}</td>
                          <td className="p-3 text-muted">{row.expected_doc || "None (Abstain)"}</td>
                          <td className="p-3 text-espresso font-semibold">{row.top_doc || "N/A"}</td>
                          <td className="p-3">
                            <span className={`px-1.5 py-0.5 rounded-sm text-[10px] ${
                              row.faithfulness >= 0.7 
                                ? "bg-forest/10 text-forest border border-forest/20" 
                                : "bg-ochre/10 text-ochre border border-ochre/20"
                            }`}>
                              {(row.faithfulness * 100).toFixed(0)}%
                            </span>
                          </td>
                          <td className="p-3 text-muted">{row.latency_ms} ms</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          )}

          {/* TAB 6: CONFIGURATION STUDIO */}
          {activeTab === "configuration" && (
            <div className="max-w-4xl mx-auto space-y-6">
              <div className="border-b border-taupe pb-4">
                <span className="font-pixel text-[9px] text-muted">CONFIG / 006</span>
                <h2 className="font-serif text-3xl font-bold tracking-tight text-espresso mt-1">
                  Configuration Studio
                </h2>
                <p className="text-xs text-muted font-serif italic mt-0.5">
                  Inspect verified backend parameters, environment boundaries, and runtime thresholds.
                </p>
              </div>

              <div className="paper-surface p-6 space-y-4">
                <div className="flex items-center justify-between hairline-b pb-2">
                  <h3 className="font-serif text-base font-bold text-espresso">
                    Active Runtime Settings (Source: /api/v1/config)
                  </h3>
                  <span className="font-mono text-[10px] text-muted">
                    ENVIRONMENT: <strong className="text-espresso">{systemConfig?.ENVIRONMENT || "development"}</strong>
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                  <div className="p-3 bg-sand/30 border border-taupe">
                    <span className="text-[10px] text-muted uppercase block">EMBEDDING MODEL</span>
                    <span className="font-semibold text-espresso">{systemConfig?.EMBEDDING_MODEL_NAME || "all-MiniLM-L6-v2"}</span>
                    <span className="text-[10px] text-muted block mt-0.5">Provider: {systemConfig?.EMBEDDING_PROVIDER || "sentence-transformers"}</span>
                  </div>

                  <div className="p-3 bg-sand/30 border border-taupe">
                    <span className="text-[10px] text-muted uppercase block">RERANKER MODEL</span>
                    <span className="font-semibold text-espresso">{systemConfig?.RERANKER_MODEL_NAME || "cross-encoder/ms-marco-MiniLM-L-6-v2"}</span>
                    <span className="text-[10px] text-muted block mt-0.5">Reranking Enabled: {systemConfig?.ENABLE_RERANKER ? "true" : "false"}</span>
                  </div>

                  <div className="p-3 bg-sand/30 border border-taupe">
                    <span className="text-[10px] text-muted uppercase block">SEMANTIC CACHE THRESHOLD</span>
                    <span className="font-semibold text-espresso">
                      &ge; {systemConfig?.SEMANTIC_CACHE_THRESHOLD ?? 0.90} Cosine Similarity
                    </span>
                    <span className="text-[10px] text-muted block mt-0.5">TTL: {systemConfig?.SEMANTIC_CACHE_TTL_SECONDS ?? 86400}s</span>
                  </div>

                  <div className="p-3 bg-sand/30 border border-taupe">
                    <span className="text-[10px] text-muted uppercase block">RATE LIMIT CEILING</span>
                    <span className="font-semibold text-espresso">
                      {systemConfig?.RATE_LIMIT_PER_MINUTE ?? 60} requests / minute
                    </span>
                    <span className="text-[10px] text-muted block mt-0.5">Sliding-window token bucket</span>
                  </div>

                  <div className="p-3 bg-sand/30 border border-taupe">
                    <span className="text-[10px] text-muted uppercase block">MAX UPLOAD THRESHOLD</span>
                    <span className="font-semibold text-espresso">
                      {systemConfig ? `${(systemConfig.MAX_UPLOAD_SIZE_BYTES / (1024 * 1024)).toFixed(2)} MB` : "15.00 MB"}
                    </span>
                    <span className="text-[10px] text-muted block mt-0.5">Enforced at API gateway</span>
                  </div>

                  <div className="p-3 bg-sand/30 border border-taupe">
                    <span className="text-[10px] text-muted uppercase block">MAX QUERY LENGTH</span>
                    <span className="font-semibold text-espresso">
                      {systemConfig?.MAX_QUERY_LENGTH ?? 1000} characters
                    </span>
                    <span className="text-[10px] text-muted block mt-0.5">Pydantic v2 validated</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
